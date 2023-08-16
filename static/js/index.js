$(function() {
    $('button').bind('click', function() {
        item_1 = $('select[id="input-1"]').val()
        item_2 = $('select[id="input-2"]').val()

        $('button').text("Generating...")
        // Simulate a call to a remote server
        $.getJSON($SCRIPT_ROOT + '/generate', {item_1: item_1, item_2: item_2}, 
            function(data) {
                $('button').text("=")
                // Visually update page
                new_item = data.result
                new_item_info = data.info
                new_item_created = data.new_item_created
                new_item_recipe = data.new_item_recipe
                $("#result").text(new_item);
                $("#result-info").val(new_item_info);
                update_item_info(new_item, $("#result"))
                if(new_item_created) {
                    $('select[id="input-1"]').append($("<option></option>").attr("value", new_item).text(new_item))
                    $('select[id="input-2"]').append($("<option></option>").attr("value", new_item).text(new_item))
                    $('select[id="recipes-list"]').append($("<li>"+new_item_recipe+"</li>"))
                    $('select[id="items-list"]').append($("<li>"+new_item+"</li>"))
                }
            }
        );
        return false;
    });

    // Update item descriptions
    
    $('select').each(function () {
        // Update initially
        valueSelected = this.value
        update_item_info(valueSelected, $(this))
        // Update on select change
        $(this).change(function (e) {
            valueSelected = this.value
            update_item_info(valueSelected, $(this))
        })
    });
});

function update_item_info(value, title_element) {
    title_element.parent().parent().find(".item-description").val("Loading...");
    title_element.parent().parent().find(".item-recipe").val("Loading...");
    $.getJSON($SCRIPT_ROOT + '/get_item_info', {item: value}, 
        function(data) {
            description = data.description;
            recipe = data.recipe;
            title_element.parent().parent().find(".item-description").val(description);
            title_element.parent().parent().find(".item-recipe").val(recipe);
        }
    );
}