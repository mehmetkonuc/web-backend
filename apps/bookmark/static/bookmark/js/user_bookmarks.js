$(document).ready(function() {
    // Handle bookmark removal
    $('.remove-bookmark').on('click', function() {
        var button = $(this);
        var appName = button.data('app');
        var modelName = button.data('model');
        var objectId = button.data('id');
        
        $.ajax({
            url: '{% url "bookmark:bookmark_object" %}',
            type: 'POST',
            data: {
                'app_name': appName,
                'model_name': modelName,
                'object_id': objectId,
                'csrfmiddlewaretoken': '{{ csrf_token }}'
            },
            success: function(data) {
                if (data.status === 'success') {
                    // Remove the card from the UI
                    button.closest('.bookmark-card').parent().fadeOut(function() {
                        $(this).remove();
                        
                        // If no bookmarks left, show the empty message
                        if ($('.bookmark-card').length === 0) {
                            $('.row').html('<div class="alert alert-info col-12">Henüz bir içerik kaydetmediniz.</div>');
                        }
                    });
                } else {
                    alert('İşlem sırasında bir hata oluştu: ' + data.message);
                }
            },
            error: function() {
                alert('Bir hata oluştu. Lütfen daha sonra tekrar deneyin.');
            }
        });
    });
});