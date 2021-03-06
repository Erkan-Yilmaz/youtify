var Timeline = {
    init: function() {
        $('#bottom .timeline').mousedown(function(event) {
            Timeline.manualUpdate(event);
        });
        $('#bottom .timeline .slider .knob').mousedown(function(event) {
            Timeline.startDrag(event);
        });
        $(window).mouseup(function(event) {
            Timeline.stopDrag(event);
        });
        $(window).mousemove(function(event) {
            Timeline.onDrag(event);
        });
    },
    isDragging: false,
    updateHandle: null,
    startDrag: function(event) {
        Timeline.isDragging = true;
    },
    stopDrag: function(event) {
        if (Timeline.isDragging) {
            Timeline.stop();
            Timeline.isDragging = false;
            Timeline.manualUpdate(event);
            Timeline.start();
        }
    },
    onDrag: function(event) {
        if (!Timeline.isDragging) {
            return;
        }
        Timeline.manualUpdate(event);
    },
	start: function() {
		$('#bottom .timeline .knob').show();
        if (Timeline.updateHandle === null) {
            Timeline.updateHandle = setInterval(Timeline.update, 100);
        }
	},
    manualUpdate: function(event) {
        var maxWidth = $('#bottom .timeline').width(),
            mouseX = event.pageX - $('#bottom .timeline .slider').offset().left,
            pos = null,
            len = player.getTotalPlaybackTime();
        
        if (mouseX < 0) {
            mouseX = 0;
        }
        if (mouseX > maxWidth) {
            mouseX = maxWidth;
        }
        pos = mouseX / maxWidth * len;

        $('#bottom .timeline-wrapper .position').html(Math.floor(pos/60)+':' + ((Math.round(pos%60) <10) ? '0' : '') + Math.round(pos%60));
        $('#bottom .timeline-wrapper .length').html(Math.floor(len/60)+':' + ((Math.round(len%60) <10) ? '0' : '') + Math.round(len%60));
		$('#bottom .timeline-wrapper .slider').width(pos/len*$('#bottom .timeline').width());
        
        if (!Timeline.isDragging) {
            player.seekTo(pos);
        }
    },
	update: function(percent) { 
		if (Timeline.isDragging) {
            return;
        }
        var pos = player.getCurrentPlaybackTime(),
            len = player.getTotalPlaybackTime();
        
        if (pos && len) {
            $('#bottom .timeline-wrapper .position').html(Math.floor(pos/60)+':' + ((Math.round(pos%60) <10) ? '0' : '') + Math.round(pos%60));
            $('#bottom .timeline-wrapper .length').html(Math.floor(len/60)+':' + ((Math.round(len%60) <10) ? '0' : '') + Math.round(len%60));
            $('#bottom .timeline-wrapper .slider').width(pos/len*$('#bottom .timeline').width());
        } else {
            $('#bottom .timeline-wrapper .position').html('0:00');
            $('#bottom .timeline-wrapper .length').html('0:00');
            $('#bottom .timeline-wrapper .slider').width(0);
        }
	},

	stop: function() {
		if (Timeline.updateHandle) {
			clearInterval(Timeline.updateHandle);
			Timeline.updateHandle = null;
		}
	}
};
