var auth, interval, seconds;

function api(method, args, success, error) {
    for (var name in args) {
        args[name] = JSON.stringify(args[name]);
    }

    $.ajax({
        url: '/api/' + method,
        data: args,
        dataType: 'json',
        success: success,
        error: function (xhr) {
            if (error) error($.parseJSON(xhr.responseText));
        }
    });
}

var section, visibleSection, storyLength = 0;
function update() {
    api('get_story', {id: storyId}, function (data) {
        var story = data.response;
        switch (story.state) {
            case 'open':
                section = '#suggest-paragraph';
                break;
            case 'locked':
                if (auth) {
                    section = '#suggest-paragraph';
                } else {
                    section = '#locked';
                }
                break;
            case 'pending':
                if (story.can_vote) {
                    section = '#voting';
                    $('#voting p.review').text(story.paragraph);
                } else {
                    section = '#pending';
                    $('#pending strong.yes').text(story.yes_votes + ' yes vote' + (story.yes_votes == 1 ? '' : 's'));
                    $('#pending strong.no').text(story.no_votes + ' no vote' + (story.no_votes == 1 ? '' : 's'));
                    $('#pending p.review').text(story.paragraph);
                }
                break;
        }

        if (story.length > storyLength) {
            $('#story p').remove();
            for (var i = 0; i < story.paragraphs.length; i++) {
                var p = story.paragraphs[i];
                $('#story').append($('<p/>').text(p.text).attr('title', '#' + p.number));
            }
            storyLength = story.length;
        }

        if (section != visibleSection) {
            if (visibleSection) $(visibleSection).slideUp();
            if (section) $(section).slideDown();
            visibleSection = section;
        }

        setTimeout(update, 5000);
    }, function (data) {
        setTimeout(update, 2500);
    });
}

update();

var locking = false;
$('#paragraph')
    .before('<p id="chars">140</p>')
    .keydown(function () {
        if (interval || auth || locking) return;
        locking = true;
        api('lock_story', {id: storyId},
            function (data) {
                auth = data.response.auth;
                seconds = Math.round(data.response.time);
                $('#lock-info')
                    .removeClass('error')
                    .html('You have <strong>' + seconds + ' seconds</strong> left before your reservation ends and someone else can write a paragraph.');
                interval = setInterval(function () {
                    seconds--;
                    if (seconds < 0) {
                        clearInterval(interval);
                        interval = 0;
                        return;
                    }
                    $('#lock-info strong').text(seconds + ' second' + (seconds == 1 ? '' : 's'));
                }, 1000);
                locking = false;
            },
            function (data) {
                $('#lock-info')
                    .addClass('error')
                    .html(data.response);
                locking = false;
            });
    })
    .keyup(function () {
        var left = 140 - this.value.length;
        $('#chars').text(left).toggleClass('close-to-limit', left >= 0 && left <= 25).toggleClass('past-limit', left < 0);
        $('#suggest').attr('disabled', left > 135 || left < 0);
    });

$('#suggest').click(function () {
    $('#suggest').attr('disabled', true);
    api('suggest_paragraph', {story_id: storyId, text: $('#paragraph').val(), auth: auth});
    $('#paragraph').val('');
});

$('#vote-yes').click(function () {
    api('vote_yes', {story_id: storyId});
});

$('#vote-no').click(function () {
    api('vote_no', {story_id: storyId});
});

$('button.branch').click(function () {
    api('branch_story', {id: storyId}, function (data) { location.href = '/' + data.response; });
});

