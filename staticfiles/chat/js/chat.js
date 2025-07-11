/**
 * Chat sistemi için JavaScript fonksiyonları
 * - WebSocket tabanlı gerçek zamanlı mesajlaşma
 * - Kullanıcı arayüzü işlevleri
 * - Mesaj yönetimi ve görüntüleme
 */

document.addEventListener('DOMContentLoaded', function () {

   // DOM ELEMENTLERI
   const elements = {
      chatContactsBody: document.querySelector('.app-chat-contacts .sidebar-body'),
      chatHistoryBody: document.querySelector('.chat-history-body'),
      chatSidebarLeftBody: document.querySelector('.app-chat-sidebar-left .sidebar-body'),
      chatSidebarLeftUserAbout: document.getElementById('chat-sidebar-left-user-about'),
      formSendMessage: document.querySelector('.form-send-message'),
      messageInput: document.querySelector('.message-input'),
      searchInput: document.querySelector('.chat-search-input'),
      chatContactListItems: [...document.querySelectorAll('.chat-contact-list-item:not(.chat-contact-list-item-title)')],
      textareaInfo: document.getElementById('textarea-maxlength-info'),
      conversationButton: document.getElementById('app-chat-conversation-btn'),
      chatHistoryHeader: document.querySelector(".chat-history-header [data-target='#app-chat-contacts']"),
      appChatConversation: document.getElementById('app-chat-conversation'),
      appChatHistory: document.getElementById('app-chat-history'),
      messagesList: document.querySelector('.messages-list-room'),
      messageForm: document.getElementById('message-form'),
      deleteChat: document.querySelector('.delete-chat'),
      peopleHeading: document.getElementById('people-heading'),
      searchUsersContainer: document.getElementById('search-users-container'),
      imagePreviewContainer: document.getElementById('image-preview-container'),
      fileInput: document.getElementById('attach-doc')
   };

   // GLOBAL DEĞİŞKENLER
   let chatSocket = null; // WebSocket bağlantısı
   let isConnecting = false; // WebSocket bağlantısı yapılıyor mu?
   let isLoadingMessages = false; // Mesajlar yükleniyor mu?
   let hasMoreMessages = true; // Daha fazla mesaj var mı?
   let oldestMessageId = null; // En eski mesaj ID
   let initialScrollDone = false; // İlk sayfa yüklendiğinde scroll yapıldı mı?
   let selectedFiles = []; // Seçilen resimler
   // WEBSOCKET BAĞLANTISI
   function setupWebSocket() {
      // Oda ID ve kullanıcı ID kontrolleri
      const chatContainer = document.querySelector('.chat-container');
      if (!chatContainer) {
         console.log('Chat container bulunamadı');
         return;
      }

      const roomId = chatContainer.dataset.roomId;
      const userId = parseInt(chatContainer.dataset.userId);

      if (!roomId) {
         console.log('Oda ID bulunamadı');
         return;
      }

      // Zaten bağlı ise veya bağlanma işlemi devam ediyorsa işlem yapma
      if (isConnecting || (chatSocket && chatSocket.readyState === WebSocket.OPEN)) {
         console.log('WebSocket zaten bağlı veya bağlanıyor');
         return;
      }

      isConnecting = true;

      // WebSocket URL'i oluştur
      const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
      const wsUrl = `${wsProtocol}${window.location.host}/ws/chat/${roomId}/`;

      chatSocket = new WebSocket(wsUrl);

      // Bağlantı açıldığında
      chatSocket.onopen = function () {
         isConnecting = false;
      };

      // Mesaj geldiğinde
      chatSocket.onmessage = function (event) {
         try {
            const data = JSON.parse(event.data);

            // Mesaj tipine göre işlem yap
            if (data.type === 'connection_established') {
               console.log('Bağlantı kuruldu, kullanıcı:', data.user_id);

            } else if (data.type === 'new_message') {

               handleNewMessage(data.message);
               // Sohbet odası sidebar'ını güncelle (yeni mesaj geldiğinde)
               updateChatListItem(data.message);
            } else if (data.type === 'message_notification') {
               // Aktif sohbette değilken gelen bildirimler
               console.log('Yeni mesaj bildirimi:', data.message, 'Oda:', data.room_id);

               // Sohbet odası sidebar'ını güncelle (bildirim geldiğinde)
               updateChatListItem(data.message, data.room_id);

               // Bildirim göster (opsiyonel)
               if (Notification.permission === 'granted') {
                  const sender = data.message.sender?.username || 'Kullanıcı';
                  const messageText = data.message.text || '';
                  new Notification(`Yeni Mesaj: ${sender}`, {
                     body: messageText.substring(0, 60) + (messageText.length > 60 ? '...' : ''),
                     icon: data.message.sender?.avatar || '/static/assets/img/avatars/default.png'
                  });
               }
            }

         } catch (error) {
            console.error('WebSocket mesajı işlenirken hata:', error);
         }
      };

      // Bağlantı kapandığında
      chatSocket.onclose = function (e) {
         isConnecting = false;

         // 1000 normal kapanma, diğer durumlarda yeniden bağlanmayı dene
         if (e.code !== 1000) {
            console.log('3 saniye sonra yeniden bağlanılacak...');
            setTimeout(setupWebSocket, 3000);
         }
      };

      // Hata olduğunda
      chatSocket.onerror = function (error) {
         console.error('WebSocket hatası:', error);
         isConnecting = false;
      };
   }

   // WebSocket komut gönderme
   function sendCommand(command, data = {}) {
      if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) {
         console.warn('WebSocket bağlı değil, komut gönderilemedi:', command);
         return false;
      }

      const message = {
         command: command,
         ...data
      };

      chatSocket.send(JSON.stringify(message));
      return true;
   }

   // Yeni mesaj işleme
   function handleNewMessage(message) {
      if (!elements.messagesList) return;

      // Mesaj şablonu oluştur ve listeye ekle
      renderMessage(message);

      // Mesajı okundu olarak işaretle (eğer ben göndermediyem)
      const chatContainer = document.querySelector('.chat-container');
      const userId = parseInt(chatContainer?.dataset.userId);

      if (userId && message.sender_id !== userId) {
         sendCommand('mark_as_read', {
            message_id: message.id
         });
      }

      // Son mesaja scroll
      scrollToBottom();
   } // Sohbet listesini güncelle (yeni mesaj geldiğinde)
   function updateChatListItem(message, roomId = null) {
      const chatList = document.getElementById('chat-list');
      if (!chatList) return;

      // Kullanıcının kendi isteği olan mesajlar için işlem yapma
      const userId = parseInt(document.querySelector('.chat-container')?.dataset.userId);
      if (userId === message.sender_id && !roomId) return;

      // Mesajın geldiği oda ID'si
      const messageRoomId = roomId || message.chat_room_id;
      if (!messageRoomId) return;

      // Aktif sohbet odasıysa okundu olarak işaretle ve güncelleme yapma
      const chatContainer = document.querySelector('.chat-container');
      const activeRoomId = chatContainer?.dataset.roomId;

      if (activeRoomId === messageRoomId.toString()) {
         sendCommand('mark_as_read', {
            message_id: message.id
         });
         return;
      }

      // Mevcut odanın liste öğesini bul
      const existingChatItem = chatList.querySelector(`li.chat-contact-list-item a[href*="${messageRoomId}"]`)?.closest('li');

      // Gönderici kullanıcı bilgileri
      const sender = message.sender;
      const senderUserName = message.sender_name || 'Kullanıcı';
      const senderFullName = message.sender_full_name || senderUserName;
      const avatar = message.sender_avatar;
      const messageText = message.content || '';
      const timestamp = new Date(message.timestamp || message.created_at);
      const timeAgo = formatTime(timestamp);

      // Mevcut okunmamış mesaj sayısını bul
      let unreadCount = 1; // Varsayılan olarak 1 (yeni gelen mesaj)

      if (existingChatItem) {
         // Mevcut öğede bir unread badge varsa, sayıyı artır
         const existingBadge = existingChatItem.querySelector('.badge');
         if (existingBadge) {
            const currentCount = parseInt(existingBadge.textContent) || 0;
            unreadCount = currentCount + 1;
         }
      }
      let avatarHTML = '';
      if (message.sender_avatar) {
            avatarHTML = `<img src="${message.sender_avatar}" class="user-avatar">`;
      } else {
            const firstInitial = message.sender_first_name?.charAt(0)?.toUpperCase() || '';
            const lastInitial = message.sender_last_name?.charAt(0)?.toUpperCase() || '';
            avatarHTML = `
               <span class="avatar-initial rounded-circle bg-label-primary">
                  ${firstInitial}${lastInitial}
               </span>`;
      }
      // Yeni sohbet öğesi HTML'i oluştur
      const newChatItemHTML = `
            <li class="chat-contact-list-item mb-1">
                <a href="/chat/${messageRoomId}/" class="d-flex align-items-center">
                    <div class="flex-shrink-0 avatar">
                        ${avatarHTML}
                    </div>
                    <div class="chat-contact-info flex-grow-1 ms-4">
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="chat-contact-name text-truncate fw-normal m-0">
                                ${senderFullName}
                            </h6>
                            <small class="chat-contact-list-item-time">
                                ${timeAgo}
                            </small>
                        </div>
                        <div class="d-flex bd-highlight">
                            <div class="w-100 bd-highlight">
                                <small class="chat-contact-list-item-time mr-auto">
                                    ${message.sender_id !== userId ? '' : 'Sen: '}${messageText.substring(0, 30)}${messageText.length > 30 ? '...' : ''}
                                </small>
                            </div>
                            <div class="flex-shrink-1 bd-highlight">
                                ${message.sender_id !== userId ? `<span class="badge bg-primary rounded-pill ms-2">${unreadCount}</span>` : ''}
                            </div>
                        </div>
                    </div>
                </a>
            </li>
        `;
      if (existingChatItem) {
         // Varolan öğeyi güncelle ve en üste taşı
         existingChatItem.remove();

         // İlk başlığın altına ekle
         const titleItem = chatList.querySelector('.chat-contact-list-item-title');
         if (titleItem) {
            titleItem.insertAdjacentHTML('afterend', newChatItemHTML);
         } else {
            chatList.insertAdjacentHTML('afterbegin', newChatItemHTML);
         }
      } else {
         // Yeni öğe oluştur ve en üste ekle
         const titleItem = chatList.querySelector('.chat-contact-list-item-title');
         if (titleItem) {
            titleItem.insertAdjacentHTML('afterend', newChatItemHTML);
         } else {
            chatList.insertAdjacentHTML('afterbegin', newChatItemHTML);
         }

         // "Sohbet Bulunamadı" mesajını gizle
         const emptyChat = document.querySelector('.chat-list-item-0');
         if (emptyChat) {
            emptyChat.classList.add('d-none');
         }
      }

      // Yeni eklenen öğeye event listener ekle
      setupChatItemListeners();
   }

   // PERFECTSCROLLBAR KURULUMU
   // PerfectScrollbar'ı başlat
   let psChatHistory = null;

   function setupPerfectScrollbar() {
      // Statik elementler için PerfectScrollbar başlat
      const initPerfectScrollbar = elements => {
         elements.forEach(el => {
            if (el) {
               new PerfectScrollbar(el, {
                  suppressScrollX: true
               });
            }
         });
      };

      // Sidebar ve diğer statik alanlar için PerfectScrollbar
      initPerfectScrollbar([
         elements.chatContactsBody,
         elements.chatSidebarLeftBody,
      ]);

      // Chat geçmişi için ayrı PerfectScrollbar - sayfalama ve scroll olayları için
      if (elements.chatHistoryBody) {
         psChatHistory = new PerfectScrollbar(elements.chatHistoryBody, {
            suppressScrollX: true
         });

         // Sayfalama için scroll olayını dinle (yukarı kaydırdıkça eski mesajları yükler)
         elements.chatHistoryBody.addEventListener('scroll', debounce(() => {
            // Scrollbar'ın en üstüne yakınsa (150px) eski mesajları yükle
            if (elements.chatHistoryBody.scrollTop < 150 && !isLoadingMessages && hasMoreMessages) {
               loadOlderMessages();
            }
         }, 200));
      }
   }

   // KAYDIRMA İŞLEMLERİ
   // En alta kaydırma
   function scrollToBottom() {
      if (!elements.chatHistoryBody) return;
      elements.chatHistoryBody.scrollTop = elements.chatHistoryBody.scrollHeight;
   }

   // Scroll pozisyonunu koruma (eski mesajlar eklenirken)
   function preserveScrollPosition(callback) {
      const chatHistoryBody = elements.chatHistoryBody;
      if (!chatHistoryBody) return;

      // Mevcut scroll yüksekliği ve pozisyonu kaydet
      const oldScrollHeight = chatHistoryBody.scrollHeight;
      const oldScrollTop = chatHistoryBody.scrollTop;

      // İçerik ekleme/değiştirme işlemini yap
      callback();

      // Yeni yükseklik farkını hesapla
      const newScrollHeight = chatHistoryBody.scrollHeight;
      const heightDifference = newScrollHeight - oldScrollHeight;

      // Aynı içeriği görünür tutmak için scroll pozisyonunu ayarla
      chatHistoryBody.scrollTop = oldScrollTop + heightDifference;

      // PerfectScrollbar'ı güncelle
      if (psChatHistory) {
         psChatHistory.update();
      }
   }
   // Ertelenmiş scroll
   function scrollToBottomDeferred() {
      // Önce hemen scroll
      scrollToBottom();

      // Ardından kısa gecikmelerle tekrar scroll
      // Bu, resimlerin yüklenmesi tamamlandığında scroll pozisyonunun korunmasını sağlar
      const scrollTimes = [100, 300, 500, 1000, 1500];

      scrollTimes.forEach(time => {
         setTimeout(() => {
            if (!isLoadingMessages) {
               scrollToBottom();
            }
         }, time);
      });

      // Son scroll ve güncelleme
      setTimeout(() => {
         if (!isLoadingMessages) {
            scrollToBottom();

            // PerfectScrollbar'ı güncelle
            if (psChatHistory) {
               psChatHistory.update();
            }
         }
      }, 2000);
   }

   // DOM DEĞİŞİKLİKLERİNİ İZLEME
   // MutationObserver ile message-list'e eklenen mesajları izle
   function setupMutationObserver() {
      if (!elements.messagesList) return;

      const chatObserver = new MutationObserver((mutations) => {
         // DOM değişikliklerini incele
         mutations.forEach(mutation => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
               // Eklenen node'ları kontrol et
               const addedNodes = Array.from(mutation.addedNodes);

               // "old-message" sınıfına sahip olmayan ve yükleme sırasında olmayan mesajlar
               // için scroll yap (yeni gelen mesajlar)
               const hasOldMessage = addedNodes.some(node =>
                  node.classList && node.classList.contains('old-message'));

               if (!hasOldMessage && !isLoadingMessages && initialScrollDone) {
                  scrollToBottom();
               }
            }
         });

         // PerfectScrollbar'ı güncelle
         if (psChatHistory) {
            psChatHistory.update();
         }
      });

      // Mesaj listesi değişimlerini izle
      chatObserver.observe(elements.messagesList, {
         childList: true,
         subtree: false
      });
   }

   // MESAJ GÖNDERME VE ALMA İŞLEMLERİ    // WebSocket ile mesaj gönderme
   function sendMessage(e) {
      e.preventDefault();

      if (!elements.messageForm) return;

      const message = elements.messageInput.value.trim();
      const chatRoomId = elements.messageForm.querySelector('input[name="chat_room_id"]').value;
      const hasFiles = selectedFiles.length > 0;

      if (!message && !hasFiles) return;

      // Dosya varsa, önce dosyaları yükle
      if (hasFiles) {
         // Form verisini oluştur
         const formData = new FormData();
         formData.append('chat_room_id', chatRoomId);
         if (message) {
            formData.append('message', message);
         }

         // Dosyaları ekle
         selectedFiles.forEach((file, index) => {
            formData.append(`image_${index}`, file);
         });

         // CSRF token'ı al
         const csrfToken = elements.messageForm.querySelector('input[name="csrfmiddlewaretoken"]').value;

         // Yükleme sırasında buton durumunu güncelle
         const sendButton = elements.formSendMessage.querySelector('button[type="submit"]');
         if (sendButton) {
            sendButton.disabled = true;
            sendButton.innerHTML = '<i class="icon-base ti tabler-loader icon-sm spinner"></i>';
         }

         // Dosyaları ayrı bir istek ile yükle
         fetch('/chat/upload-attachments/', {
               method: 'POST',
               headers: {
                  'X-CSRFToken': csrfToken
               },
               body: formData
            })
            .then(response => response.json())
            .then(data => {
               // Yükleme başarılıysa, mesajı WebSocket ile bildir
               if (data.success && chatSocket && chatSocket.readyState === WebSocket.OPEN) {
                  sendCommand('message_with_attachments', {
                     message_id: data.message_id
                  });

                  // UI'yi temizle
                  elements.messageInput.value = '';
                  resetImageUpload();
                  elements.messageInput.focus();

                  // Buton durumunu sıfırla
                  if (sendButton) {
                     sendButton.disabled = false;
                     sendButton.innerHTML = '<i class="icon-base ti tabler-send icon-sm"></i>';
                  }
               }
            })
            .catch(error => {
               console.error("Dosya yükleme hatası:", error);
               alert("Resimler yüklenirken bir hata oluştu. Lütfen tekrar deneyin.");

               // Buton durumunu sıfırla
               if (sendButton) {
                  sendButton.disabled = false;
                  sendButton.innerHTML = '<i class="icon-base ti tabler-send icon-sm"></i>';
               }
            });

         return;
      }

      // Sadece metin mesajı ise WebSocket ile gönder
      if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
         // Mesajı WebSocket ile gönder
         sendCommand('send_message', {
            message: message
         });

         // Input'u temizle
         elements.messageInput.value = '';

         // Dosya önizlemelerini temizle
         resetImageUpload();

         // Mesajı gönderdikten sonra focus'u input'a ver
         elements.messageInput.focus();

         return;
      } else {
         console.warn('WebSocket bağlantısı kurulmadı, mesaj gönderilemedi');

         // WebSocket bağlantısını yeniden kurmayı dene
         setupWebSocket();

         // WebSocket bağlantısı olmadığından kullanıcıya bilgi ver
         alert('Mesaj gönderilemedi. Lütfen sayfayı yenileyip tekrar deneyin.');
      }
   }

   // Tek bir mesajı göster
   function renderMessage(message) {
      if (!elements.messagesList) {
         console.error('Mesaj listesi elementi bulunamadı!');
         return;
      }

      const chatContainer = document.querySelector('.chat-container');
      const userId = parseInt(chatContainer?.dataset.userId);
      const isMine = userId && message.sender_id === userId;

      // Resim ekleri için HTML oluştur
      let attachmentsHtml = '';
      if (message.attachments && message.attachments.length > 0) {
         attachmentsHtml = '<div class="chat-message-attachments">';
         message.attachments.forEach(attachment => {
            attachmentsHtml += `<img src="${attachment.file}" class="chat-message-attachment-img" alt="Image attachment" onclick="window.open('${attachment.file}', '_blank')">`;
         });
         attachmentsHtml += '</div>';
      }

      // Mesaj metni için HTML oluştur (boş değilse)
      let messageTextHtml = '';
      const messageText = message.text || message.content || '';
      if (messageText && messageText.trim() !== '') {
         messageTextHtml = `<div class="chat-message-text"><p class="mb-0 text-break">${messageText}</p></div>`;
      }

      // Zaman formatı
      const messageTime = message.formatted_time || formatTime(message.created_at || message.timestamp);

      // Mesaj elementi oluştur
      const messageElement = document.createElement('li');
      messageElement.className = `chat-message ${isMine ? 'chat-message-right' : ''}`;
      messageElement.dataset.id = message.id;
      messageElement.dataset.timestamp = message.created_at || message.timestamp;

      // Mesaj içeriği
      messageElement.innerHTML = `
            <div class="d-flex overflow-hidden">
                <div class="chat-message-wrapper flex-grow-1">
                    ${messageTextHtml}
                    ${attachmentsHtml}
                    <div class="${isMine ? 'text-end' : ''} text-body-secondary mt-1">
                        <small>${messageTime}</small>
                    </div>
                </div>
            </div>
        `;

      // Mesajı listeye ekle
      elements.messagesList.appendChild(messageElement);

      // Eğer resim ekleri varsa, yüklendikten sonra scroll yapmak için onload kullan
      if (message.attachments && message.attachments.length > 0) {
         const images = messageElement.querySelectorAll('img');
         let loadedCount = 0;
         const totalImages = images.length;

         // Her bir resim için onload listener ekle
         images.forEach(img => {
            if (img.complete) {
               loadedCount++;
               if (loadedCount === totalImages) {
                  scrollToBottomDeferred();
               }
            } else {
               img.onload = function () {
                  loadedCount++;
                  if (loadedCount === totalImages) {
                     scrollToBottomDeferred();
                  }
               };

               // Hata durumunda da ilerle
               img.onerror = function () {
                  loadedCount++;
                  if (loadedCount === totalImages) {
                     scrollToBottomDeferred();
                  }
               };
            }
         });
      } else {
         // Resim yoksa normal scroll yap
         scrollToBottom();
      }
   }

   // Eski mesajları AJAX ile yükle
   function loadOlderMessages() {
      const chatRoomId = elements.messageForm?.querySelector('input[name="chat_room_id"]')?.value;
      if (!chatRoomId || isLoadingMessages || !hasMoreMessages) return;

      isLoadingMessages = true;

      // Sayfalama parametreleri ile URL oluştur
      let url = `/chat/${chatRoomId}/messages/?page_size=20`;
      if (oldestMessageId) {
         url += `&before_id=${oldestMessageId}`;
      }

      // Yükleme göstergesi ekle
      const loadingHTML = `
            <li class="chat-message chat-message-center" id="loading-messages">
                <div class="p-3 text-center">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">Yükleniyor...</span>
                    </div>
                    <span class="ms-2">Eski mesajlar yükleniyor...</span>
                </div>
            </li>
        `;
      elements.messagesList.insertAdjacentHTML('afterbegin', loadingHTML);

      // Eski mesajları getir
      fetch(url)
         .then(response => response.json())
         .then(data => {
            // Yükleme göstergesini kaldır
            document.getElementById('loading-messages')?.remove();

            if (data.messages && data.messages.length > 0) {
               // Mesajlar için HTML oluştur
               let messageHTML = '';
               data.messages.forEach(message => {
                  const chatContainer = document.querySelector('.chat-container');
                  const userId = parseInt(chatContainer?.dataset.userId);
                  const isMine = userId && message.sender_id === userId;

                  // Resim ekleri için HTML oluştur
                  let attachmentsHtml = '';
                  if (message.attachments && message.attachments.length > 0) {
                     attachmentsHtml = '<div class="chat-message-attachments">';
                     message.attachments.forEach(attachment => {
                        attachmentsHtml += `<img src="${attachment.file}" class="chat-message-attachment-img" alt="Image attachment" onclick="window.open('${attachment.file}', '_blank')">`;
                     });
                     attachmentsHtml += '</div>';
                  }

                  // Mesaj metni için HTML oluştur (boş değilse)
                  let messageTextHtml = '';
                  if (message.text && message.text.trim() !== '') {
                     messageTextHtml = `<div class="chat-message-text"><p class="mb-0 text-break">${message.text}</p></div>`;
                  }

                  // Mesaj HTML'i (eski mesaj sınıfı ekli)
                  messageHTML += `
                            <li class="chat-message old-message ${isMine ? 'chat-message-right' : ''}" data-id="${message.id}" data-timestamp="${message.timestamp}">
                                <div class="d-flex overflow-hidden">
                                    <div class="chat-message-wrapper flex-grow-1">
                                        ${messageTextHtml}
                                        ${attachmentsHtml}
                                        <div class="${isMine ? 'text-end' : ''} text-body-secondary mt-1">
                                            <small>${message.formatted_time}</small>
                                        </div>
                                    </div>
                                </div>
                            </li>
                        `;

                  // En eski mesaj ID'si için kontrol
                  if (!oldestMessageId || parseInt(message.id) < oldestMessageId) {
                     oldestMessageId = parseInt(message.id);
                  }
               });

               // Scroll pozisyonunu koruyarak mesajları ekle
               preserveScrollPosition(() => {
                  elements.messagesList.insertAdjacentHTML('afterbegin', messageHTML);
               });

               // Sayfalama bilgilerini güncelle
               hasMoreMessages = data.pagination?.has_more || false;
               oldestMessageId = data.pagination?.oldest_message_id || oldestMessageId;
            } else {
               // Daha fazla mesaj yok
               hasMoreMessages = false;
            }

            isLoadingMessages = false;
         })
         .catch(error => {
            console.error('Eski mesajlar yüklenirken hata:', error);
            document.getElementById('loading-messages')?.remove();
            isLoadingMessages = false;
         });
   }

   // RESİM YÜKLEME VE ÖNİZLEME
   // Maksimum resim sayısı ve izin verilen türler
   const MAX_IMAGES = 4;
   const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'];

   // Resim seçildiğinde
   function handleImageSelection() {
      const fileInput = elements.fileInput;
      const previewContainer = elements.imagePreviewContainer;
      const chatHistoryBody = elements.chatHistoryBody;

      if (!fileInput || !previewContainer) return;

      // Yeni seçilen dosyalar
      const newFiles = Array.from(fileInput.files).filter(file => ALLOWED_IMAGE_TYPES.includes(file.type));

      if (newFiles.length > 0) {
         // Yeni dosyaları global array'e ekle (maksimum sayıyı aşmadan)
         const remainingSlots = MAX_IMAGES - selectedFiles.length;

         if (remainingSlots <= 0) {
            // Boş slot yok, uyarı göster
            alert('Maksimum 4 resim seçebilirsiniz');
            fileInput.value = '';
            return;
         }

         // Sadece kalan slot kadar dosya ekle
         const filesToAdd = newFiles.slice(0, remainingSlots);

         if (filesToAdd.length < newFiles.length) {
            // Bazı dosyalar limit nedeniyle eklenemedi
            alert('Maksimum 4 resim seçebilirsiniz');
         }

         // Yeni dosyaları array'e ekle
         selectedFiles = [...selectedFiles, ...filesToAdd];

         // Önizleme güncellemesi
         updateImagePreview();

         // Dosya seçiciyi sıfırla
         fileInput.value = '';

         // Önizleme gösterildikten sonra aşağı kaydır
         setTimeout(scrollToBottom, 100);
      }
   }

   // Resim önizlemelerini güncelle
   function updateImagePreview() {
      const previewContainer = elements.imagePreviewContainer;
      const chatHistoryBody = elements.chatHistoryBody;

      if (!previewContainer) return;

      // Mevcut önizlemeleri temizle
      previewContainer.innerHTML = '';

      if (selectedFiles.length > 0) {
         // Önizleme konteynerini göster
         previewContainer.style.display = 'flex';

         // Mesaj geçmişi yüksekliğini ayarla
         if (chatHistoryBody) {
            chatHistoryBody.style.height = 'calc(100vh - 22rem - 100px)';
         }

         // Her dosya için önizleme oluştur
         selectedFiles.forEach((file, index) => {
            const reader = new FileReader();

            reader.onload = (e) => {
               const previewItem = document.createElement('div');
               previewItem.className = 'image-preview-item';
               previewItem.dataset.index = index;

               previewItem.innerHTML = `
                        <img src="${e.target.result}" alt="Preview">
                        <div class="image-preview-remove" data-index="${index}">
                            <i class="icon-base ti tabler-x icon-12px"></i>
                        </div>
                    `;

               previewContainer.appendChild(previewItem);

               // Kaldırma butonuna tıklama olayı ekle
               previewItem.querySelector('.image-preview-remove').addEventListener('click', () => {
                  removeImage(index);
               });
            };

            reader.readAsDataURL(file);
         });
      } else {
         // Dosya yoksa önizleme konteynerini gizle
         previewContainer.style.display = 'none';

         // Mesaj geçmişi yüksekliğini sıfırla
         if (chatHistoryBody) {
            chatHistoryBody.style.height = '';
         }
      }
   }

   // Seçili resmi kaldır
   function removeImage(index) {
      if (index >= 0 && index < selectedFiles.length) {
         // Dosyayı array'den kaldır
         selectedFiles.splice(index, 1);

         // Önizlemeyi güncelle
         updateImagePreview();
      }
   }

   // Resim yükleme formunu sıfırla
   function resetImageUpload() {
      if (!elements.fileInput || !elements.imagePreviewContainer) return;

      elements.fileInput.value = '';
      elements.imagePreviewContainer.style.display = 'none';
      elements.imagePreviewContainer.innerHTML = '';
      selectedFiles = []; // Global array'i temizle

      // Mesaj geçmişi yüksekliğini sıfırla
      if (elements.chatHistoryBody) {
         elements.chatHistoryBody.style.height = '';
      }
   }

   // YARDİMCİ FONKSİYONLAR
   // Zaman formatı
   function formatTime(isoTime) {
      if (!isoTime) return '';

      try {
         const date = new Date(isoTime);
         const now = new Date();
         const diffMs = now - date;
         const diffSec = Math.floor(diffMs / 1000);
         const diffMin = Math.floor(diffSec / 60);
         const diffHour = Math.floor(diffMin / 60);
         const diffDay = Math.floor(diffHour / 24);

         // Eğer 1 dakikadan az ise "şimdi"
         if (diffMin < 1) {
            return 'şimdi';
         }
         // Eğer 1 saatten az ise "X dakika önce"
         else if (diffHour < 1) {
            return `${diffMin} dk`;
         }
         // Eğer 24 saatten az ise "X saat önce"
         else if (diffDay < 1) {
            return `${diffHour} sa`;
         }
         // Eğer 7 günden az ise "X gün önce"
         else if (diffDay < 7) {
            return `${diffDay} gün`;
         }
         // Diğer durumlarda tarih formatı
         else {
            return date.toLocaleDateString('tr-TR', {
               day: '2-digit',
               month: '2-digit',
               year: '2-digit'
            });
         }
      } catch (e) {
         console.error('Tarih formatı hatası:', e);
         return '';
      }
   }

   // Debounce fonksiyonu
   function debounce(func, wait) {
      let timeout;
      return (...args) => {
         clearTimeout(timeout);
         timeout = setTimeout(() => func.apply(this, args), wait);
      };
   }

   // Bildirim izinlerini kontrol et
   function checkNotificationPermission() {
      // Bildirim API'sini destekliyor mu?
      if (!('Notification' in window)) {
         console.log('Bu tarayıcı masaüstü bildirimlerini desteklemiyor');
         return;
      }

      // İzin durumunu kontrol et
      if (Notification.permission === 'default') {
         // İzin iste
         Notification.requestPermission().then(permission => {
            console.log('Bildirim izni:', permission);
         });
      }

      console.log('Mevcut bildirim izni:', Notification.permission);
   }

   // UI FONKSİYONLARİ
   // Textarea karakter sayacı
   function handleMaxLengthCount(inputElement, infoElement, maxLength) {
      if (!inputElement || !infoElement) return;

      const currentLength = inputElement.value.length;
      const remaining = maxLength - currentLength;

      infoElement.className = 'maxLength label-success';

      if (remaining >= 0) {
         infoElement.textContent = `${currentLength}/${maxLength}`;
      }

      if (remaining <= 0) {
         infoElement.textContent = `${currentLength}/${maxLength}`;
         infoElement.classList.remove('label-success');
         infoElement.classList.add('label-danger');
      }
   }

   // Chat conversation görünümüne geç
   function switchToChatConversation() {
      // Küçük ekranlarda sidebar'ı aç
      if (window.innerWidth < 992) {
         const sidebarElement = document.getElementById('app-chat-contacts');
         if (sidebarElement) {
            sidebarElement.classList.add('show');
         }
      } else {
         // Büyük ekranlarda normal görünüm
         if (elements.appChatConversation && elements.appChatHistory) {
            elements.appChatConversation.classList.replace('d-flex', 'd-none');
            elements.appChatHistory.classList.replace('d-none', 'd-block');
         }
      }
   }

   // Sidebar'ı kapat
   function closeSidebar() {
      const sidebarElement = document.getElementById('app-chat-contacts');
      if (sidebarElement) {
         sidebarElement.classList.remove('show');
      }
   }

   // Sohbet kişileri araması
   function filterChatContacts(selector, searchValue, placeholderSelector) {
      const items = document.querySelectorAll(`${selector}:not(.chat-contact-list-item-title)`);
      let visibleCount = 0;

      items.forEach(item => {
         const isVisible = item.textContent.toLowerCase().includes(searchValue);
         item.classList.toggle('d-flex', isVisible);
         item.classList.toggle('d-none', !isVisible);
         if (isVisible) visibleCount++;
      });

      const placeholder = document.querySelector(placeholderSelector);
      if (placeholder) {
         placeholder.classList.toggle('d-none', visibleCount > 0);
      }
   }

   // Kullanıcı arama
   function fetchUsers(query) {
      fetch(`/chat/users/search/?q=${encodeURIComponent(query)}`)
         .then(response => response.json())
         .then(data => {
            if (data.users && data.users.length > 0) {
               if (elements.peopleHeading) {
                  elements.peopleHeading.style.display = 'block';
               }
               displayUserSearchResults(data.users);
            } else {
               if (elements.peopleHeading) {
                  elements.peopleHeading.style.display = 'none';
               }
               if (elements.searchUsersContainer) {
                  elements.searchUsersContainer.innerHTML = '';
               }
            }
         })
         .catch(error => console.error('Kullanıcı araması hatası:', error));
   }

   // Kullanıcı arama sonuçlarını göster
   function displayUserSearchResults(users) {
      if (!elements.searchUsersContainer) return;

      elements.searchUsersContainer.innerHTML = '';

      users.forEach(user => {
         const userHTML = `
                <li class="chat-contact-list-item mb-1 search-user-item" data-user-id="${user.id}">
                    <a href="javascript:void(0);" class="d-flex align-items-center">
                        <div class="flex-shrink-0 avatar">
                            ${user.avatar ? 
                                `<img src="${user.avatar}" alt="Avatar" class="rounded-circle" />` : 
                                `<span class="avatar-initial rounded-circle bg-label-secondary">
                                    ${user.username.slice(0, 2).toUpperCase()}
                                </span>`
                            }
                        </div>
                        <div class="chat-contact-info flex-grow-1 ms-4">
                            <h6 class="chat-contact-name text-truncate fw-normal m-0">
                                ${user.full_name}
                            </h6>
                            <small class="chat-contact-status text-truncate">
                                ${user.username}
                            </small>
                        </div>
                    </a>
                </li>
            `;
         elements.searchUsersContainer.insertAdjacentHTML('beforeend', userHTML);
      });

      // Yeni sohbet başlatma için tıklama olayı
      document.querySelectorAll('.search-user-item').forEach(item => {
         item.addEventListener('click', () => {
            const userId = item.dataset.userId;
            startNewChat(userId);
         });
      });
   }

   // Yeni sohbet başlat
   function startNewChat(userId) {
      const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;

      fetch('/chat/rooms/', {
            method: 'POST',
            headers: {
               'X-CSRFToken': csrfToken,
               'Content-Type': 'application/json'
            },
            body: JSON.stringify({
               user_id: userId
            })
         })
         .then(response => response.json())
         .then(data => {
            if (data.id) {
               // Yeni sohbete yönlendir
               window.location.href = `/chat/${data.id}/`;
            }
         })
         .catch(error => console.error('Sohbet oluşturma hatası:', error));
   }

   // Sohbet silme
   function deleteChat() {
      const chatId = elements.deleteChat?.getAttribute('data-chat-id');
      if (!chatId) return;

      // Silme onayı
      if (!confirm('Bu sohbeti silmek istediğinizden emin misiniz?')) return;

      // CSRF token
      const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;

      // AJAX ile sohbeti sil
      fetch(`/chat/${chatId}/delete/`, {
            method: 'POST',
            headers: {
               'X-CSRFToken': csrfToken,
               'Content-Type': 'application/json'
            }
         })
         .then(response => response.json())
         .then(data => {
            if (data.status) {
               // Sohbet listesine yönlendir
               window.location.href = '/chat/';
            }
         })
         .catch(error => console.error('Sohbet silme hatası:', error));
   }

   // En eski mesaj ID'sini başlat
   function initOldestMessageId() {
      if (elements.messagesList) {
         const messages = elements.messagesList.querySelectorAll('li.chat-message:not(.chat-message-center)');
         if (messages.length > 0) {
            // Tüm mesaj ID'lerini al
            let messageIds = Array.from(messages)
               .map(msg => parseInt(msg.dataset.id))
               .filter(id => !isNaN(id));

            // En küçük ID'yi bul (en eski mesaj)
            if (messageIds.length > 0) {
               oldestMessageId = Math.min(...messageIds);
            }
         }
      }
   } // Sohbet öğelerine event listener ekle
   function setupChatItemListeners() {
      // Dinamik olarak oluşturulmuş sohbet öğeleri için listener ekle
      const newChatItems = document.querySelectorAll('.chat-contact-list-item:not(.chat-contact-list-item-title)');

      newChatItems.forEach(item => {
         // Zaten listener atanmışsa tekrar ekleme
         if (item.dataset.hasListener) return;

         const link = item.querySelector('a');
         if (link) {
            link.addEventListener('click', (e) => {
               // Tüm aktif sınıfları kaldır
               document.querySelectorAll('.chat-contact-list-item').forEach(contact => {
                  contact.classList.remove('active');
               });

               // Bu öğeyi aktif olarak işaretle
               item.classList.add('active');
            });

            // Listener eklendiğini işaretle
            item.dataset.hasListener = 'true';
         }
      });
   }

   // EVENT LISTENERS
   function setupEventListeners() {
      // Dosya seçimi
      elements.fileInput?.addEventListener('change', handleImageSelection);

      // Textarea karakter sayacı
      if (elements.chatSidebarLeftUserAbout && elements.textareaInfo) {
         const maxLength = parseInt(elements.chatSidebarLeftUserAbout.getAttribute('maxlength'), 10) || 100;
         handleMaxLengthCount(elements.chatSidebarLeftUserAbout, elements.textareaInfo, maxLength);

         elements.chatSidebarLeftUserAbout.addEventListener('input', () => {
            handleMaxLengthCount(elements.chatSidebarLeftUserAbout, elements.textareaInfo, maxLength);
         });
      }

      // Sohbet görünümüne geçiş
      elements.conversationButton?.addEventListener('click', switchToChatConversation);

      // Sohbet listesi öğeleri
      elements.chatContactListItems.forEach(item => {
         const link = item.querySelector('a');
         if (link) {
            link.addEventListener('click', () => {
               elements.chatContactListItems.forEach(contact => {
                  contact.classList.remove('active');
               });
               item.classList.add('active');
            });
         }
      });

      // Arama filtresi
      elements.searchInput?.addEventListener('keyup', debounce(e => {
         const searchValue = e.target.value.toLowerCase();

         // Mevcut sohbetleri filtrele
         filterChatContacts('#chat-list li', searchValue, '.chat-list-item-0');

         // Kullanıcı ara
         if (searchValue.length >= 2) {
            fetchUsers(searchValue);
         } else {
            if (elements.peopleHeading) {
               elements.peopleHeading.style.display = 'none';
            }
            if (elements.searchUsersContainer) {
               elements.searchUsersContainer.innerHTML = '';
            }
         }
      }, 300));

      // Mesaj gönderme
      elements.messageForm?.addEventListener('submit', sendMessage);

      // Sohbet silme
      elements.deleteChat?.addEventListener('click', deleteChat);

      // Sidebar kapatma
      document.getElementById('close-sidebar-btn')?.addEventListener('click', closeSidebar);

      // Sohbet listesi öğelerine tıklandığında sidebar'ı kapat (mobil)
      elements.chatContactListItems.forEach(item => {
         item.addEventListener('click', () => {
            if (window.innerWidth < 992) {
               // Yönlendirme için kısa bir gecikme
               setTimeout(closeSidebar, 100);
            }
         });
      });

      // Sayfa görünür olduğunda WebSocket bağlantısını kontrol et
      document.addEventListener('visibilitychange', function () {
         if (!document.hidden && elements.messageForm) {
            // WebSocket bağlantısını kontrol et
            if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) {
               setupWebSocket();
            }
         }
      });
   } // BAŞLATMA
   function initialize() {
      // PerfectScrollbar'ı başlat
      setupPerfectScrollbar();

      // DOM değişikliklerini izle
      setupMutationObserver();

      // Event listener'ları ekle
      setupEventListeners();

      // Mevcut sohbet öğelerine listener ekle
      setupChatItemListeners();

      // Bildirim izinlerini kontrol et
      checkNotificationPermission();

      // WebSocket bağlantısını kur
      setupWebSocket();

      // İlk yüklemede scroll
      scrollToBottom();

      // En eski mesaj ID'sini başlat
      initOldestMessageId();

      // Sayfa yüklendikten sonra scroll'u iyileştir
      setTimeout(() => {
         scrollToBottomDeferred();

         // İlk scroll işlemi tamamlandı
         setTimeout(() => {
            initialScrollDone = true;
         }, 1500);
      }, 500);

      // 30 saniyede bir WebSocket bağlantısını kontrol et
      setInterval(function () {
         if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) {
            setupWebSocket();
         }
      }, 30000);

      // Bildirim izinlerini kontrol et
      checkNotificationPermission();
   }

   // Uygulamayı başlat
   initialize();
});