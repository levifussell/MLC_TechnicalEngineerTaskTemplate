$(function() {
    $('button').bind('click', function() {
        item_1 = $('select[id="input-1"]').val()
        item_2 = $('select[id="input-2"]').val()

        $('button').text("Generating...")
        // Simulate a call to a remote server
        $.getJSON($SCRIPT_ROOT + '/generate', {item_1: item_1, item_2:item_2}, 
            function(data) {
                $('button').text("=")
                // Visually update page
                new_item = data.result
                $("#result").text(new_item);
                update_description(new_item, $("#result"))
                $('select[id="input-1"]').append($("<option></option>").attr("value", new_item).text(new_item))
                $('select[id="input-2"]').append($("<option></option>").attr("value", new_item).text(new_item))
            }
        );
        return false;
    });

    // Update item descriptions
    
    $('select').each(function () {
        // Update initially
        valueSelected = this.value
        update_description(valueSelected, $(this))
        // Update on select change
        $(this).change(function (e) {
            valueSelected = this.value
            update_description(valueSelected, $(this))
        })
    });
});

function update_description(value, title_element) {
    title_element.parent().parent().find(".item-description").text("Loading...");
    $.getJSON($SCRIPT_ROOT + '/get_description', {item: value}, 
        function(data) {
            description = data.result
            title_element.parent().parent().find(".item-description").text(description);
        }
    );
}
