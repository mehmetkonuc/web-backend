# Firebase Service Account Setup Guide

## Firebase Projesinden Service Account Key Alma

1. Firebase Console'a gidin: https://console.firebase.google.com/
2. Projenizi seçin
3. Project Settings > Service Accounts sekmesine gidin
4. "Generate new private key" butonuna tıklayın
5. İndirilen JSON dosyasını `firebase-service-account.json` olarak yeniden adlandırın
6. Bu dosyayı Django projesinin root dizinine koyun: `web/firebase-service-account.json`

## Önemli Güvenlik Notları

- Bu dosya asla git repository'sine eklenmemelidir
- `.gitignore` dosyasında bu dosya zaten göz ardı edilmiştir
- Production ortamında bu dosyayı sunucuda güvenli bir şekilde saklayın
- Environment variable olarak da tanımlayabilirsiniz

## Test için Örnek Dosya

Geliştirme ve test için `firebase-service-account-example.json` örnek dosyası oluşturulmuştur.
Gerçek Firebase projesi kullanmak için yukarıdaki adımları takip edin.
