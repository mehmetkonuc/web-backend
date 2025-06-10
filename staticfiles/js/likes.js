$(document).ready(function() {
    // Handle like button click
    $(document).on('click', '.like-button', function() {
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
                'csrfmiddlewaretoken': $('input[name="csrfmiddlewaretoken"]').val()
            },
            success: function(response) {
                if (response.status === 'success') {                    
                    // Update button appearance based on like status
                    if (response.is_liked) {
                        button.addClass('active');
                        button.find('i').removeClass('tabler-heart').addClass('tabler-heart-filled');
                        button.find('.like-text').text('Beğenildi');
                    } else {
                        button.removeClass('active');
                        button.find('i').removeClass('tabler-heart-filled').addClass('tabler-heart');
                        button.find('.like-text').text('Beğen');
                    }
                    
                    // Update like count
                    button.find('.like-count').text(response.like_count);
                    
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
    
    // Function to check like status
    function checkLikeStatus(container) {
        var appName = container.data('app');
        var modelName = container.data('model');
        var objectId = container.data('id');
        
        $.ajax({
            url: '/like/status/',
            type: 'GET',
            data: {
                'app_name': appName,
                'model_name': modelName,
                'object_id': objectId
            },
            success: function(response) { 
                if (response.status === 'success') {
                    var button = container;
                    // Update button appearance based on like status
                    if (response.is_liked) {
                        button.addClass('active');
                        button.find('i').removeClass('tabler-heart').addClass('tabler-heart-filled');
                        button.find('.like-text').text('Beğenildi');
                    } else {
                        button.removeClass('active');
                        button.find('i').removeClass('tabler-heart-filled').addClass('tabler-heart');
                        button.find('.like-text').text('Beğen');
                    }
                    
                    // Update like count
                    button.find('.like-count').text(response.like_count);
                }
            }
        });
    }
    
    // Check status for all like buttons on page load
    $('.like-button').each(function() {
        checkLikeStatus($(this));
    });
});
    
    // Create form data for the POST request
    const formData = new FormData();
    formData.append('app_name', appName);
    formData.append('model_name', modelName);
    formData.append('object_id', objectId);
    
    // Send like/unlike request
    fetch('/like/like/', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            // Update button state
            button.dataset.liked = data.liked;
            
            // Update the count display
            const countElement = button.querySelector('.like-count');
            if (countElement) {
                countElement.textContent = data.like_count > 0 ? data.like_count : '';
            }
            
            // Update the icon/text
            updateLikeButtonUI(button, data.liked);
        } else {
            console.error('Error:', data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    })
    .finally(() => {
        // Re-enable button
        button.disabled = false;
    });
}

function updateLikeButtonState(button) {
    const appName = button.dataset.appName;
    const modelName = button.dataset.modelName;
    const objectId = button.dataset.objectId;
    
    if (!appName || !modelName || !objectId) {
        console.error('Missing required data attributes for like button');
        return;
    }
    
    // Fetch current like status
    fetch(`/like/status/?app_name=${appName}&model_name=${modelName}&object_id=${objectId}`, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            // Set the liked state on the button
            button.dataset.liked = data.liked;
            
            // Update the count display
            const countElement = button.querySelector('.like-count');
            if (countElement) {
                countElement.textContent = data.like_count > 0 ? data.like_count : '';
            }
            
            // Update the icon/text
            updateLikeButtonUI(button, data.liked);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function updateLikeButtonUI(button, liked) {
    // Get the icon element
    const icon = button.querySelector('i');
    
    if (liked) {
        // Liked state
        button.classList.add('liked');
        if (icon) {
            // Fix: Check if it already has the filled class before replacing
            if (!icon.className.includes('tabler-heart-filled')) {
                icon.className = icon.className.replace('tabler-heart', 'tabler-heart-filled');
            }
        }
    } else {
        // Not liked state
        button.classList.remove('liked');
        if (icon) {
            // Fix: Check if it has the filled class before replacing
            if (icon.className.includes('tabler-heart-filled')) {
                icon.className = icon.className.replace('tabler-heart-filled', 'tabler-heart');
            }
        }
    }
}

// Function to observe and initialize like buttons for infinite scroll content
function setupInfiniteScrollObserver() {
    // Check if the container exists
    const infiniteContainer = document.querySelector('.infinite-container');
    if (!infiniteContainer) return;
    
    // Create an observer instance
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                // New content has been added, initialize like buttons on new content
                initLikeSystem();
            }
        });
    });
    
    // Configuration of the observer
    const config = { childList: true, subtree: true };
    
    // Start observing the target node for configured mutations
    observer.observe(infiniteContainer, config);
    
    // Also check for waypoints/infinite scroll events
    document.addEventListener('infiniteScrollComplete', function() {
        // Initialize like buttons after new content is loaded
        setTimeout(initLikeSystem, 100); // Small delay to ensure DOM is updated
    });
    
    // Additional fallback for jQuery-based infinite scroll
    if (window.jQuery) {
        jQuery(document).ajaxComplete(function() {
            // Initialize like buttons after AJAX completes
            setTimeout(initLikeSystem, 100);
        });
    }
}

// Helper function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}