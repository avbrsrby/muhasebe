from django.core.management.base import BaseCommand
from muhasebe.models import Il, Ilce

class Command(BaseCommand):
    help = 'Türkiye il ve ilçelerini yükler'

    def handle(self, *args, **kwargs):
        # İller ve ilçeler (kısaltılmış örnek)
        il_ilce_data = {
            'Adana': {
                'plaka': 1,
                'ilceler': ['Seyhan', 'Çukurova', 'Yüreğir', 'Sarıçam', 'Aladağ', 'Ceyhan', 'Feke', 'İmamoğlu', 'Karaisalı', 'Karataş', 'Kozan', 'Pozantı', 'Saimbeyli', 'Tufanbeyli', 'Yumurtalık']
            },
            'Adıyaman': {
                'plaka': 2,
                'ilceler': ['Merkez', 'Besni', 'Çelikhan', 'Gerger', 'Gölbaşı', 'Kahta', 'Samsat', 'Sincik', 'Tut']
            },
            'Afyonkarahisar': {
                'plaka': 3,
                'ilceler': ['Merkez', 'Başmakçı', 'Bayat', 'Bolvadin', 'Çay', 'Çobanlar', 'Dazkırı', 'Dinar', 'Emirdağ', 'Evciler', 'Hocalar', 'İhsaniye', 'İscehisar', 'Kızılören', 'Sandıklı', 'Sinanpaşa', 'Sultandağı', 'Şuhut']
            },
            'Ankara': {
                'plaka': 6,
                'ilceler': ['Altındağ', 'Ayaş', 'Bala', 'Beypazarı', 'Çamlıdere', 'Çankaya', 'Çubuk', 'Elmadağ', 'Etimesgut', 'Evren', 'Gölbaşı', 'Güdül', 'Haymana', 'Kahramankazan', 'Kalecik', 'Keçiören', 'Kızılcahamam', 'Mamak', 'Nallıhan', 'Polatlı', 'Pursaklar', 'Sincan', 'Şereflikoçhisar', 'Yenimahalle']
            },
            'Antalya': {
                'plaka': 7,
                'ilceler': ['Akseki', 'Aksu', 'Alanya', 'Demre', 'Döşemealtı', 'Elmalı', 'Finike', 'Gazipaşa', 'Gündoğmuş', 'İbradı', 'Kaş', 'Kemer', 'Kepez', 'Konyaaltı', 'Korkuteli', 'Kumluca', 'Manavgat', 'Muratpaşa', 'Serik']
            },
            'İstanbul': {
                'plaka': 34,
                'ilceler': ['Adalar', 'Arnavutköy', 'Ataşehir', 'Avcılar', 'Bağcılar', 'Bahçelievler', 'Bakırköy', 'Başakşehir', 'Bayrampaşa', 'Beşiktaş', 'Beykoz', 'Beylikdüzü', 'Beyoğlu', 'Büyükçekmece', 'Çatalca', 'Çekmeköy', 'Esenler', 'Esenyurt', 'Eyüpsultan', 'Fatih', 'Gaziosmanpaşa', 'Güngören', 'Kadıköy', 'Kağıthane', 'Kartal', 'Küçükçekmece', 'Maltepe', 'Pendik', 'Sancaktepe', 'Sarıyer', 'Silivri', 'Sultanbeyli', 'Sultangazi', 'Şile', 'Şişli', 'Tuzla', 'Ümraniye', 'Üsküdar', 'Zeytinburnu']
            },
            'İzmir': {
                'plaka': 35,
                'ilceler': ['Aliağa', 'Balçova', 'Bayındır', 'Bayraklı', 'Bergama', 'Beydağ', 'Bornova', 'Buca', 'Çeşme', 'Çiğli', 'Dikili', 'Foça', 'Gaziemir', 'Güzelbahçe', 'Karabağlar', 'Karaburun', 'Karşıyaka', 'Kemalpaşa', 'Kınık', 'Kiraz', 'Konak', 'Menderes', 'Menemen', 'Narlıdere', 'Ödemiş', 'Seferihisar', 'Selçuk', 'Tire', 'Torbalı', 'Urla']
            },
            # Tüm illeri eklemek için bu yapıyı devam ettirin
        }
        
        # İlleri ve ilçeleri oluştur
        for il_adi, il_data in il_ilce_data.items():
            il, created = Il.objects.get_or_create(
                ad=il_adi,
                defaults={'plaka': il_data['plaka']}
            )
            
            if created:
                self.stdout.write(f"İl oluşturuldu: {il_adi}")
            
            # İlçeleri oluştur
            for ilce_adi in il_data['ilceler']:
                ilce, created = Ilce.objects.get_or_create(
                    il=il,
                    ad=ilce_adi
                )
                if created:
                    self.stdout.write(f"  - İlçe oluşturuldu: {ilce_adi}")
        
        self.stdout.write(self.style.SUCCESS('İl ve ilçeler başarıyla yüklendi!'))