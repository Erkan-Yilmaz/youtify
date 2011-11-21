# -*- coding: utf-8 -*-

import os
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import users
from django.utils import simplejson
from model import get_current_youtify_user
from model import create_youtify_user
from model import YoutifyUser

class Snapshot(db.Model):
    date = db.DateTimeProperty(auto_now_add=True)
    json = db.TextProperty(required=True)
    active = db.BooleanProperty()

class Leader(db.Model):
    lang = db.StringProperty(required=True)
    user = db.ReferenceProperty(reference_class=YoutifyUser)

class Phrase(db.Model):
    date = db.DateTimeProperty(auto_now_add=True)
    original = db.StringProperty(required=True)
    approved_translations = db.StringListProperty()

    en_US = db.StringProperty()
    sv_SE = db.StringProperty()
    ro_SE = db.StringProperty()
    fi_FI = db.StringProperty()

class HistoryItem(db.Model):
    TYPE_COMMENT = 1
    TYPE_SUGGESTION = 2
    TYPE_APPROVED = 3
    TYPE_ORIGINAL_CHANGED = 3

    phrase = db.ReferenceProperty(reference_class=Phrase)
    user = db.ReferenceProperty(reference_class=YoutifyUser)
    date = db.DateTimeProperty(auto_now_add=True)
    type = db.IntegerProperty(required=True)
    text = db.StringProperty()
    lang = db.StringProperty()

languages = [
    {
        'code': 'en_US',
        'label': 'English',
        'enabled': True,
    },
    {
        'code': 'sv_SE',
        'label': 'Svenska',
        'enabled': True,
    },
    {
        'code': 'ro_SE',
        'label': 'Rövarspråket',
        'enabled': True,
    },
    {
        'code': 'fi_FI',
        'label': 'Suomi',
        'enabled': True,
    },
]

LANG_CODES = [i['code'] for i in languages]

# This map is used when detecting the user agents locale settings.
LANG_MAP = {}
for lang in languages:
    LANG_MAP[lang['code'].lower().replace('_', '-')] = lang['code']
    LANG_MAP[lang['code'].split('_')[0]] = lang['code']

def auto_detect_language(request):
    header = request.headers.get('Accept-Language', '')
    header = header.lower()

    accepted_languages = header.split(';')[0]
    accepted_languages = accepted_languages.split(',')

    for lang in accepted_languages:
        if lang in LANG_MAP:
            return LANG_MAP[lang]

    return 'en_US'

def get_history(phrase, code):
    json = []
    items = HistoryItem.all().filter('phrase =', phrase).filter('lang =', code)
    if items is not None:
        for item in items:
            json.append({
                'date': item.date.strftime('%Y-%M-%d %H:%m'),
                'type': item.type,
                'text': item.text,
                'user': {
                    'name': item.user.google_user.nickname().split('@')[0],
                    'id': int(item.user.key().id()),
                },
            })
    return json

def get_translations(code):
    json = []
    for phrase in Phrase.all().order('-date'):
        json.append({
            'id': phrase.key().id(),
            'approved': code in phrase.approved_translations,
            'original': phrase.original,
            'translation': getattr(phrase, code, phrase.original),
            'history': get_history(phrase, code),
        })
    return json

def get_deployed_translations_json(code):
    global deployed_translations
    if code in deployed_translations:
        return simplejson.dumps(deployed_translations[code])
    return '{}'

class TranslationsHandler(webapp.RequestHandler):
    def get(self):
        code = self.request.path.split('/')[-1]

        if not code in LANG_CODES:
            raise Exception('Unknown language code "%s"' % code)

        self.response.headers['Content-Type'] = 'application/json'

        if self.request.get('comments'):
            self.response.out.write(simplejson.dumps(get_translations(code)))
        else:
            self.response.out.write(get_deployed_translations_json(code))

    def post(self):
        """Suggest a new translation

        Only team leaders and admins are allowed to change the translation
        if a suggestion has already been made.
        """
        lang_code = self.request.path.split('/')[-1]
        original = self.request.get('original')
        translation = self.request.get('translation')

        if not lang_code in LANG_CODES:
            raise Exception('Unknown language code "%s"' % lang_code)

        phrase = Phrase.all().filter('original =', original).get()

        if phrase is None:
            raise Exception('No phrase matching "%s" found' % original)

        if getattr(phrase, lang_code):
            user = get_current_youtify_user()
            if not (lang in get_leader_langs_for_user(user) or users.is_current_user_admin()):
                self.error(403)

        setattr(phrase, lang_code, translation)
        phrase.save()

def get_leader_langs_for_user(youtify_user):
    ret = []
    for leader in Leader.all().filter('user =', youtify_user):
        ret.append(leader.lang)
    return ret

class TranslationsToolHandler(webapp.RequestHandler):
    def get(self):
        current_user = users.get_current_user()
        youtify_user = get_current_youtify_user()
        if (current_user is not None) and (youtify_user is None):
            youtify_user = create_youtify_user()
        path = os.path.join(os.path.dirname(__file__), 'html', 'translations.html')
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.response.out.write(template.render(path, {
            'is_admin': simplejson.dumps(users.is_current_user_admin()),
            'my_langs': simplejson.dumps(get_leader_langs_for_user(youtify_user)),
            'my_user_email': current_user.email(),
            'my_user_name': current_user.nickname().split('@')[0],
            'my_user_id': youtify_user.key().id(),
            'logout_url': users.create_logout_url('/'),
            'languages': languages,
        }))

class CommentsHandler(webapp.RequestHandler):
    def post(self):
        phrase_id = int(self.request.path.split('/')[-2])
        lang = self.request.get('lang')
        text = self.request.get('text')
        phrase = Phrase.get_by_id(int(phrase_id))

        if phrase is None:
            raise Exception("No phrase with id %s found", phrase_id)

        history_item = HistoryItem(lang=lang, text=text, type=HistoryItem.TYPE_COMMENT, phrase=phrase, user=get_current_youtify_user())
        history_item.put()

class ApproveHandler(webapp.RequestHandler):
    def post(self):
        phrase_id = self.request.path.split('/')[-2]
        lang = self.request.get('lang')
        phrase = Phrase.get_by_id(int(phrase_id))
        user = get_current_youtify_user()

        if not (lang in get_leader_langs_for_user(user) or users.is_current_user_admin()):
            self.error(403)
            return

        if phrase is None:
            raise Exception("No phrase with id %s found", phrase_id)

        translation = getattr(phrase, lang)
        text = None

        if lang in phrase.approved_translations:
            phrase.approved_translations.remove(lang)
            text = '%s removed the approved state for the translation "%s"' % (user.google_user.nickname(), translation)
        else:
            phrase.approved_translations.append(lang)
            text = '%s approved the translation "%s"' % (user.google_user.nickname(), translation)

        history_item = HistoryItem(lang=lang, text=text, type=HistoryItem.TYPE_APPROVED, phrase=phrase, user=user)
        history_item.put()

        phrase.save()

class LeadersHandler(webapp.RequestHandler):
    def post(self):
        lang = self.request.get('lang')
        user_id = self.request.get('user')
        user = YoutifyUser.get_by_id(int(user_id))

        if user is None:
            raise Exception("No user with id %s found" % user_id)

        leader = Leader(lang=lang, user=user)
        leader.put()

    def get(self):
        lang_code = self.request.get('lang')
        json = []
        leaders = Leader.all().filter('lang =', lang_code)
        for leader in leaders:
            json.append({
                'lang': leader.lang,
                'id': str(leader.key().id()),
                'user': {
                    'id': int(leader.user.key().id()),
                    'name': leader.user.google_user.nickname(),
                },
            })
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(json))

    def delete(self):
        """Delete a specific leader"""
        if not users.is_current_user_admin():
            self.error(403)

        leader_id = self.request.path.split('/')[-1]
        leader = Leader.get_by_id(int(leader_id))

        if leader:
            leader.delete()
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('success');
        else:
            self.error(404)

class PhrasesHandler(webapp.RequestHandler):
    def get(self):
        """Get all phrases"""
        json = []
        phrases = Phrase.all().order('-date')
        for phrase in phrases:
            json.append({
                'id': phrase.key().id(),
                'original': phrase.original,
            })
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(json))

    def post(self):
        """Create a new phrase"""
        if not users.is_current_user_admin():
            self.error(403)
        else:
            original = self.request.get('original')
            phrase = Phrase(original=original)
            phrase.put()

    def delete(self):
        """Delete a specific phrase"""
        if not users.is_current_user_admin():
            self.error(403)

        phrase_id = self.request.path.split('/')[-1]
        phrase = Phrase.get_by_id(int(phrase_id))

        if phrase:
            phrase.delete()
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('success');
        else:
            self.error(404)

class SnapshotsHandler(webapp.RequestHandler):
    def get(self):
        json = [];
        for snapshot in Snapshot.all().order('-date'):
            json.append({
                'key': str(snapshot.key()),
                'date': snapshot.date.strftime('%Y-%M-%d %H:%m'),
                'active': snapshot.active,
            })
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(json))

    def post(self):
        """Deploy action"""
        json = {}
        for code in LANG_CODES:
            json[code] = translations = get_translations(code)
        json = simplejson.dumps(json)

        active_snapshot = Snapshot.all().filter('active =', True).get()
        if active_snapshot:
            active_snapshot.active = False
            active_snapshot.save()

        new_snapshot = Snapshot(json=json, active=True)
        new_snapshot.put()

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('success')

deployed_translations = {}
snapshot = Snapshot.all().filter('active =', True).get()
if snapshot:
    deployed_translations = simplejson.loads(snapshot.json)

def main():
    application = webapp.WSGIApplication([
        ('/api/translations.*', TranslationsHandler),
        ('/translations/snapshots', SnapshotsHandler),
        ('/translations/phrases.*', PhrasesHandler),
        ('/translations/leaders.*', LeadersHandler),
        ('/translations/.*/approve', ApproveHandler),
        ('/translations/.*/comments', CommentsHandler),
        ('/translations.*', TranslationsToolHandler),
    ], debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
