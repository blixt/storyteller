function api(method, args, success, error) {
    for (var name in args) {
        args[name] = JSON.stringify(args[name]);
    }

    var options = {
        url: '/api/' + method,
        data: args,
        dataType: 'json'
    };

    if (success) {
        options.success = function (data) {
            if (data.status == 'success') return success(data);
            if (error) return error(data);
        };
    }

    if (error) {
        options.error = function (xhr) {
            return error(JSON.parse(xhr.responseText));
        };
    }

    $.ajax(options);
}

$('#paragraph')
    .keyup(function () {
        var left = 250 - this.value.length;
        $('#chars')
            .text(left + ' character' + (Math.abs(left) == 1 ? '' : 's') + ' left')
            .toggleClass('close-to-limit', left >= 0 && left <= 25)
            .toggleClass('past-limit', left < 0);
        $('#add').attr('disabled', left > 240 || left < 0);
    });

$('#add')
    .click(function () {
        api('add_paragraph',
            {story_id: story.id, paragraph_number: paragraph.number,
             text: $('#paragraph').val()},
            function (data) {
                location.href = '/' + data.response.story_id + '/' + data.response.paragraph_number;
            },
            function (data) {
                $('#add, #paragraph').attr('disabled', false);
                alert(data.response);
            });
        $('#add, #paragraph').attr('disabled', true);
    });
