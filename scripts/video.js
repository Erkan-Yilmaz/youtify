jQuery.fn.play = function() {
	$('#results-container .playing').removeClass('playing');
	$(this[0]).addClass("playing");
	Player.play($(this[0]).data('videoId'), $(this[0]).find('.title').text());
};

function selectVideo(li, event) {
	if (event !== undefined) {
		if (event.ctrlKey || event.shiftKey) {
			// insert code for multiselect and remove next line
			li.siblings().removeClass('selected');
		} else {
			li.siblings().removeClass('selected');
		}
	} else {
		li.siblings().removeClass('selected');
	}
    li.addClass('selected');
}

function createRatingBar(rating) {
    var ratingOuter = $('<div class="rating" title="Rating"/>');
    var ratingInner = $('<div/>');
    var percent = (rating / 5) * 100;
    ratingInner.css('width', percent + '%');
    ratingInner.appendTo(ratingOuter);
    return ratingOuter;
}
 
function createResultsItem(title, videoId, rating) {
    var artist = extractArtist(title);
    var additionalMenuButtons = [];
	
    li = $('<li/>')
        .addClass("draggable")
        .addClass("video")
        .data('type', 'video') // used for drag n drop
        .data('videoId', videoId)
        .mousedown(function(event) {
            selectVideo($(this), event);
        })
        .bind('contextmenu', showResultsItemContextMenu)
        .click(function(event) {
            event.stopPropagation();
        });

	li.dblclick(function(event) {		
        var owner = $(this).parents().data('owner');
		if (owner) {
            Player.addSiblingsToPlayorder(this, owner.find('.shuffle-on').length === 1);
        } else {
			Player.addSiblingsToPlayorder(this, false);
		}
		event.stopPropagation();
		$(this).play();
	});
	
	$('<span/>')
		.addClass("title")
		.text(title)
		.appendTo(li);

    if (rating !== undefined) {
        //createRatingBar(rating).appendTo(li); // disabled until we can sort by it and appropriately describe what it is
    }

    if (artist) {
        additionalMenuButtons.push({
            title: 'More from ' + artist,
            li: li,
            callback: function(li) {
                var artist = extractArtist(li.text());
                $('#search input').val(artist).keyup();
            }
        });
    }

    li.data('additionalMenuButtons', additionalMenuButtons);

    return li;
}
