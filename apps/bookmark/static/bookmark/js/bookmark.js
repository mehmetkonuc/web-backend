$(document).ready(function() {
    // CSRF Token alma fonksiyonu
    function getCSRFToken() {
        // 1. Meta tag'den kontrol et
        var token = $('meta[name="csrf-token"]').attr('content');
        
        // 2. Form input'undan kontrol et (meta tag yoksa)
        if (!token) {
            token = $('input[name="csrfmiddlewaretoken"]').val();
        }
        
        // 3. Cookie'den kontrol et (diğer yöntemler başarısız olursa)
        if (!token) {
            token = getCookie('csrftoken');
        }
        
        return token;
    }
    
    // Cookie değerini alma fonksiyonu
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Handle bookmark button click
    $(document).on('click', '.bookmark-button', function() {
        var button = $(this);
        var appName = button.data('app');
        var modelName = button.data('model');
        var objectId = button.data('id');
        var url = button.data('url');
        
        // Disable the button temporarily
        button.prop('disabled', true);
        
        $.ajax({
            url: url,
            type: 'POST',
            data: {
                'app_name': appName,
                'model_name': modelName,
                'object_id': objectId,
                'csrfmiddlewaretoken': getCSRFToken()
            },
            success: function(response) {
                if (response.status === 'success') {                    // Update button appearance based on bookmark status
                    if (response.is_bookmarked) {
                        button.find('button').removeClass('btn-text-secondary').addClass('btn-text-primary');

                        button.find('i').removeClass('tabler-bookmark').addClass('tabler-bookmark-filled');
                        button.find('.bookmark-text').text('Kaydedildi');
                    } else {
                        button.find('button').removeClass('btn-text-primary').addClass('btn-text-secondary');

                        button.find('i').removeClass('tabler-bookmark-filled').addClass('tabler-bookmark');
                        button.find('.bookmark-text').text('Kaydet');
                    }
                    
                    // Update bookmark count
                    button.find('.bookmark-count').text("(" + response.bookmark_count + ")");

                    // Show notification (if you have a notification system)
                    if (typeof showNotification === 'function') {
                        showNotification(response.message, 'success');
                    }
                } else {
                    // Show error message
                    if (typeof showNotification === 'function') {
                        showNotification(response.message, 'error');
                    } else {
                        alert(response.message);
                    }
                }
            },
            error: function(xhr) {
                // Show error message
                var errorMessage = 'Bir hata oluştu. Lütfen daha sonra tekrar deneyin.';
                
                try {
                    var response = JSON.parse(xhr.responseText);
                    if (response.message) {
                        errorMessage = response.message;
                    }
                } catch (e) {
                    // Parsing error, use default message
                }
                
                if (typeof showNotification === 'function') {
                    showNotification(errorMessage, 'error');
                } else {
                    alert(errorMessage);
                }
            },
            complete: function() {
                // Re-enable the button
                button.prop('disabled', false);
            }
        });
    });

});
