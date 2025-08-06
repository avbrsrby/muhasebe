from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
from django.db.models import Sum, Q, F
import random
import string


# Base Model - Tüm modeller bundan türeyecek
class BaseModel(models.Model):
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name='Oluşturma Tarihi')
    guncelleme_tarihi = models.DateTimeField(auto_now=True, verbose_name='Güncelleme Tarihi')
    silindi = models.BooleanField(default=False, verbose_name='Silindi')
    silinme_tarihi = models.DateTimeField(null=True, blank=True, verbose_name='Silinme Tarihi')
    silen_kullanici = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='%(class)s_silen', verbose_name='Silen Kullanıcı')
    
    class Meta:
        abstract = True
    
    def soft_delete(self, user):
        """Soft delete işlemi"""
        self.silindi = True
        self.silinme_tarihi = timezone.now()
        self.silen_kullanici = user
        self.save()
    
    def restore(self):
        """Geri yükleme işlemi"""
        self.silindi = False
        self.silinme_tarihi = None
        self.silen_kullanici = None
        self.save()


# ===================== TEMEL MODELLER =====================

class CariGrup(BaseModel):
    kod = models.CharField(max_length=20, unique=True, verbose_name='Grup Kodu', editable=False)
    ad = models.CharField(max_length=100, verbose_name='Grup Adı')
    ust_grup = models.ForeignKey('self', on_delete=models.CASCADE, 
                                 null=True, blank=True, 
                                 related_name='alt_gruplar',
                                 verbose_name='Üst Grup')
    seviye = models.IntegerField(default=1, verbose_name='Seviye')
    aktif = models.BooleanField(default=True, verbose_name='Aktif')
    
    class Meta:
        db_table = 'cari_gruplar'
        verbose_name = 'Cari Grup'
        verbose_name_plural = 'Cari Gruplar'
        ordering = ['kod']
    
    def __str__(self):
        if self.ust_grup:
            return f"{self.ust_grup} > {self.ad}"
        return self.ad
    
    def save(self, *args, **kwargs):
        if not self.kod:
            if self.ust_grup:
                if self.ust_grup.ust_grup:
                    prefix = 'AG'
                else:
                    prefix = 'AR'
            else:
                prefix = 'GR'
            
            last_grup = CariGrup.objects.filter(kod__startswith=prefix).order_by('-kod').first()
            if last_grup:
                last_number = int(last_grup.kod.replace(prefix, ''))
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.kod = f"{prefix}{new_number:03d}"
        
        if self.ust_grup:
            self.seviye = self.ust_grup.seviye + 1
        else:
            self.seviye = 1
        
        super().save(*args, **kwargs)




class StokGrup(BaseModel):
    kod = models.CharField(max_length=20, unique=True, verbose_name='Grup Kodu', editable=False)
    ad = models.CharField(max_length=100, verbose_name='Grup Adı')
    ust_grup = models.ForeignKey('self', on_delete=models.CASCADE, 
                                 null=True, blank=True, 
                                 related_name='alt_gruplar',
                                 verbose_name='Üst Grup')
    seviye = models.IntegerField(default=1, verbose_name='Seviye')
    aktif = models.BooleanField(default=True, verbose_name='Aktif')
    
    class Meta:
        db_table = 'stok_gruplar'
        verbose_name = 'Stok Grup'
        verbose_name_plural = 'Stok Gruplar'
        ordering = ['kod']
    
    def __str__(self):
        if self.ust_grup:
            return f"{self.ust_grup} > {self.ad}"
        return self.ad
    
    def save(self, *args, **kwargs):
        if not self.kod:
            if self.ust_grup:
                if self.ust_grup.ust_grup:
                    prefix = 'SAG'
                else:
                    prefix = 'SAR'
            else:
                prefix = 'SGR'
            
            last_grup = StokGrup.objects.filter(kod__startswith=prefix).order_by('-kod').first()
            if last_grup:
                last_number = int(last_grup.kod.replace(prefix, ''))
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.kod = f"{prefix}{new_number:03d}"
        
        if self.ust_grup:
            self.seviye = self.ust_grup.seviye + 1
        else:
            self.seviye = 1
        
        super().save(*args, **kwargs)


class Il(models.Model):
    ad = models.CharField(max_length=50, unique=True, verbose_name='İl Adı')
    plaka = models.IntegerField(unique=True, verbose_name='Plaka Kodu')
    
    class Meta:
        db_table = 'iller'
        verbose_name = 'İl'
        verbose_name_plural = 'İller'
        ordering = ['plaka']
    
    def __str__(self):
        return self.ad


class Ilce(models.Model):
    il = models.ForeignKey(Il, on_delete=models.CASCADE, related_name='ilceler', verbose_name='İl')
    ad = models.CharField(max_length=50, verbose_name='İlçe Adı')
    
    class Meta:
        db_table = 'ilceler'
        verbose_name = 'İlçe'
        verbose_name_plural = 'İlçeler'
        ordering = ['ad']
        unique_together = [['il', 'ad']]
    
    def __str__(self):
        return f"{self.ad} - {self.il.ad}"


class ParaBirimi(BaseModel):
    kod = models.CharField(max_length=3, unique=True, verbose_name='Para Birimi Kodu')
    ad = models.CharField(max_length=50, verbose_name='Para Birimi Adı')
    sembol = models.CharField(max_length=5, verbose_name='Sembol')
    aktif = models.BooleanField(default=True, verbose_name='Aktif')
    
    class Meta:
        db_table = 'para_birimleri'
        verbose_name = 'Para Birimi'
        verbose_name_plural = 'Para Birimleri'
        ordering = ['kod']
    
    def __str__(self):
        return f"{self.kod} - {self.ad}"


# ===================== KASA/BANKA MODELLER =====================

class Kasa(BaseModel):
    kod = models.CharField(max_length=20, unique=True, verbose_name='Kasa Kodu')
    ad = models.CharField(max_length=100, verbose_name='Kasa Adı')
    para_birimi = models.ForeignKey(ParaBirimi, on_delete=models.PROTECT, 
                                    verbose_name='Para Birimi', related_name='kasalar')
    # bakiye field'ı KALDIRILDI - property olacak
    aktif = models.BooleanField(default=True, verbose_name='Aktif')
    
    class Meta:
        db_table = 'kasalar'
        verbose_name = 'Kasa'
        verbose_name_plural = 'Kasalar'
        ordering = ['kod']
    
    def __str__(self):
        return f"{self.kod} - {self.ad} ({self.para_birimi.kod})"
    
    @property
    def bakiye(self):
        """Kasa bakiyesi hareketlerden hesaplanır"""
        from django.db.models import Sum, Q, Case, When, F, DecimalField
        
        result = CariHareket.objects.filter(
            kasa=self,
            silindi=False
        ).aggregate(
            giris=Sum(
                Case(
                    # Döviz işlemi varsa TL karşılığını al
                    When(
                        Q(doviz_kuru__isnull=False) & 
                        Q(tl_karsiligi__isnull=False) & 
                        ~Q(para_birimi__kod='TL'),
                        then=F('tl_karsiligi')
                    ),
                    # Değilse normal tutarı al
                    default=F('tutar'),
                    output_field=DecimalField()
                ),
                filter=Q(hareket_yonu='giris')
            ),
            cikis=Sum(
                Case(
                    # Döviz işlemi varsa TL karşılığını al
                    When(
                        Q(doviz_kuru__isnull=False) & 
                        Q(tl_karsiligi__isnull=False) & 
                        ~Q(para_birimi__kod='TL'),
                        then=F('tl_karsiligi')
                    ),
                    # Değilse normal tutarı al
                    default=F('tutar'),
                    output_field=DecimalField()
                ),
                filter=Q(hareket_yonu='cikis')
            )
        )
        
        giris_toplam = result['giris'] or Decimal('0')
        cikis_toplam = result['cikis'] or Decimal('0')
        
        return giris_toplam - cikis_toplam


class Banka(BaseModel):
    kod = models.CharField(max_length=20, unique=True, verbose_name='Banka Kodu')
    ad = models.CharField(max_length=100, verbose_name='Banka Adı')
    sube = models.CharField(max_length=100, blank=True, verbose_name='Şube')
    hesap_no = models.CharField(max_length=30, verbose_name='Hesap No')
    iban = models.CharField(max_length=32, unique=True, verbose_name='IBAN',
                           validators=[RegexValidator(regex='^TR[0-9]{24}$', 
                                     message='Geçerli bir IBAN giriniz')])
    para_birimi = models.ForeignKey(ParaBirimi, on_delete=models.PROTECT, 
                                    verbose_name='Para Birimi', related_name='bankalar')
    # bakiye field'ı KALDIRILDI - property olacak
    aktif = models.BooleanField(default=True, verbose_name='Aktif')
    
    class Meta:
        db_table = 'bankalar'
        verbose_name = 'Banka'
        verbose_name_plural = 'Bankalar'
        ordering = ['kod']
    
    def __str__(self):
        return f"{self.kod} - {self.ad} ({self.para_birimi.kod})"
    
    @property
    def bakiye(self):
        """Banka bakiyesi hareketlerden hesaplanır"""
        from django.db.models import Sum, Q, Case, When, F, DecimalField
        
        result = CariHareket.objects.filter(
            banka=self,
            silindi=False
        ).aggregate(
            giris=Sum(
                Case(
                    # Döviz işlemi varsa TL karşılığını al
                    When(
                        Q(doviz_kuru__isnull=False) & 
                        Q(tl_karsiligi__isnull=False) & 
                        ~Q(para_birimi__kod='TL'),
                        then=F('tl_karsiligi')
                    ),
                    # Değilse normal tutarı al
                    default=F('tutar'),
                    output_field=DecimalField()
                ),
                filter=Q(hareket_yonu='giris')
            ),
            cikis=Sum(
                Case(
                    # Döviz işlemi varsa TL karşılığını al
                    When(
                        Q(doviz_kuru__isnull=False) & 
                        Q(tl_karsiligi__isnull=False) & 
                        ~Q(para_birimi__kod='TL'),
                        then=F('tl_karsiligi')
                    ),
                    # Değilse normal tutarı al
                    default=F('tutar'),
                    output_field=DecimalField()
                ),
                filter=Q(hareket_yonu='cikis')
            )
        )
        
        giris_toplam = result['giris'] or Decimal('0')
        cikis_toplam = result['cikis'] or Decimal('0')
        
        return giris_toplam - cikis_toplam


class Pos(BaseModel):
    kod = models.CharField(max_length=20, unique=True, verbose_name='POS Kodu')
    ad = models.CharField(max_length=100, verbose_name='POS Adı')
    banka = models.ForeignKey(Banka, on_delete=models.PROTECT, verbose_name='Banka')
    komisyon_orani = models.DecimalField(max_digits=5, decimal_places=2, default=0, 
                                        verbose_name='Komisyon Oranı %')
    aktif = models.BooleanField(default=True, verbose_name='Aktif')
    
    class Meta:
        db_table = 'poslar'
        verbose_name = 'POS'
        verbose_name_plural = 'POS Cihazları'
        ordering = ['kod']
    
    def __str__(self):
        return f"{self.kod} - {self.ad}"


# ===================== CARİ MODELLER =====================

class CariKart(BaseModel):
    FIRMA_TIPLERI = [
        ('sahis', 'Şahıs Firması'),
        ('sirket', 'Şirket'),
    ]
    
    kod = models.CharField(max_length=20, unique=True, verbose_name='Cari Kod', editable=False)
    unvan = models.CharField(max_length=200, verbose_name='Ünvan')
    
    # Grup Bilgileri
    grup = models.ForeignKey(CariGrup, on_delete=models.PROTECT,
                            related_name='cariler',
                            verbose_name='Cari Grubu')
    
    # Yetkili Bilgileri
    yetkili_adi = models.CharField(max_length=100, verbose_name='Yetkili Adı Soyadı')
    yetkili_tel1 = models.CharField(max_length=20, blank=True, verbose_name='Yetkili No 1')
    yetkili_tel2 = models.CharField(max_length=20, blank=True, verbose_name='Yetkili No 2')
    yetkili_tel3 = models.CharField(max_length=20, blank=True, verbose_name='Yetkili No 3')
    
    # İletişim
    telefon = models.CharField(max_length=20, verbose_name='Telefon')
    email = models.EmailField(blank=True, verbose_name='E-posta')
    
    # Adres Bilgileri
    adres = models.TextField(verbose_name='Adres')
    il = models.ForeignKey(Il, on_delete=models.PROTECT, verbose_name='İl')
    ilce = models.ForeignKey(Ilce, on_delete=models.PROTECT, verbose_name='İlçe')
    
    # Fatura Bilgileri
    firma_tipi = models.CharField(max_length=10, choices=FIRMA_TIPLERI, default='sahis', verbose_name='Firma Tipi')
    tc_kimlik = models.CharField(max_length=11, blank=True, verbose_name='TC Kimlik No',
                                validators=[RegexValidator(regex='^[0-9]{11}$', 
                                          message='TC Kimlik No 11 haneli olmalıdır')])
    sirket_unvani = models.CharField(max_length=200, blank=True, verbose_name='Şirket Ünvanı')
    vergi_no = models.CharField(max_length=11, blank=True, verbose_name='Vergi No',
                               validators=[RegexValidator(regex='^[0-9]{10,11}$', 
                                         message='Vergi no 10 veya 11 haneli olmalıdır')])
    vergi_dairesi = models.CharField(max_length=100, blank=True, verbose_name='Vergi Dairesi')
    
    # Mali Bilgiler - bakiye field'ı KALDIRILDI, property olacak
    risk_limiti = models.DecimalField(max_digits=15, decimal_places=2, default=0, 
                                     verbose_name='Risk Limiti', validators=[MinValueValidator(0)])
    
    # Not alanı
    notlar = models.TextField(blank=True, verbose_name='Notlar')
    
    # Sistem
    aktif = models.BooleanField(default=True, verbose_name='Aktif')
    
    class Meta:
        db_table = 'cari_kartlar'
        verbose_name = 'Cari Kart'
        verbose_name_plural = 'Cari Kartlar'
        ordering = ['kod']
    
    def __str__(self):
        return f"{self.kod} - {self.unvan}"
    
    def save(self, *args, **kwargs):
        if not self.kod:
            prefix = 'CK'
            last_cari = CariKart.objects.filter(kod__startswith=prefix).order_by('-kod').first()
            if last_cari:
                last_number = int(last_cari.kod.replace(prefix, ''))
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.kod = f"{prefix}{new_number:06d}"
        
        super().save(*args, **kwargs)
    
    @property
    def bakiye(self):
        """TL cinsinden bakiye (geriye uyumluluk için)"""
        from django.db.models import Sum, Q
        
        try:
            tl = ParaBirimi.objects.get(kod='TL')
            result = CariHareket.objects.filter(
                cari=self,
                silindi=False,
                para_birimi=tl
            ).aggregate(
                giris=Sum('tutar', filter=Q(hareket_yonu='giris')),
                cikis=Sum('tutar', filter=Q(hareket_yonu='cikis'))
            )
            
            giris_toplam = result['giris'] or Decimal('0')
            cikis_toplam = result['cikis'] or Decimal('0')
            
            return giris_toplam - cikis_toplam
        except ParaBirimi.DoesNotExist:
            return Decimal('0')
    
    def get_bakiye_detay(self):
        """Tüm para birimleri için bakiye detayı"""
        from django.db.models import Sum, Q, F
        
        return CariHareket.objects.filter(
            cari=self,
            silindi=False
        ).values(
            'para_birimi__id',
            'para_birimi__kod',
            'para_birimi__ad'
        ).annotate(
            toplam_giris=Sum('tutar', filter=Q(hareket_yonu='giris')),
            toplam_cikis=Sum('tutar', filter=Q(hareket_yonu='cikis'))
        ).annotate(
            bakiye=F('toplam_giris') - F('toplam_cikis')
        ).filter(
            Q(toplam_giris__gt=0) | Q(toplam_cikis__gt=0)
        )


# ===================== STOK MODELLER =====================

class StokKart(BaseModel):
    BIRIMLER = [
        ('ADET', 'Adet'),
        ('KG', 'Kilogram'),
        ('METRE', 'Metre'),
        ('LITRE', 'Litre'),
        ('PAKET', 'Paket'),
        ('KOLI', 'Koli'),
    ]
    
    kod = models.CharField(max_length=30, unique=True, verbose_name='Stok Kodu', editable=False)
    ad = models.CharField(max_length=200, verbose_name='Stok Adı')
    barkod = models.CharField(max_length=20, blank=True, verbose_name='Barkod')
    
    # Birim ve Miktar
    birim = models.CharField(max_length=10, choices=BIRIMLER, default='ADET', verbose_name='Birim')
    miktar = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Mevcut Miktar')
    kritik_stok = models.DecimalField(max_digits=15, decimal_places=2, default=0, 
                                     verbose_name='Kritik Stok Seviyesi', validators=[MinValueValidator(0)])
    
    # Para birimi ekleyelim
    para_birimi = models.ForeignKey(ParaBirimi, on_delete=models.PROTECT, 
                                    verbose_name='Para Birimi', related_name='stoklar',
                                    null=True, blank=True)  # Geçici olarak null yapıyoruz
    
    # Grup bilgisi
    grup = models.ForeignKey(StokGrup, on_delete=models.PROTECT,
                            related_name='stoklar',
                            verbose_name='Stok Grubu',
                            null=True, blank=True)
    
    # Fiyatlar
    alis_fiyati = models.DecimalField(max_digits=15, decimal_places=2, default=0, 
                                     verbose_name='Alış Fiyatı', validators=[MinValueValidator(0)])
    satis_fiyati = models.DecimalField(max_digits=15, decimal_places=2, default=0, 
                                      verbose_name='Satış Fiyatı', validators=[MinValueValidator(0)])
    kdv_orani = models.IntegerField(default=20, verbose_name='KDV Oranı %')
    
    # Sistem
    aktif = models.BooleanField(default=True, verbose_name='Aktif')
    
    class Meta:
        db_table = 'stok_kartlar'
        verbose_name = 'Stok Kart'
        verbose_name_plural = 'Stok Kartlar'
        ordering = ['kod']
    
    def __str__(self):
        return f"{self.kod} - {self.ad}"
    
    def save(self, *args, **kwargs):
        if not self.kod:
            # Otomatik kod oluştur
            prefix = 'STK'
            last_stok = StokKart.objects.filter(kod__startswith=prefix).order_by('-kod').first()
            if last_stok:
                try:
                    last_number = int(last_stok.kod.replace(prefix, ''))
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            
            self.kod = f"{prefix}{new_number:06d}"
        
        # Para birimi yoksa varsayılan TL yap
        if not self.para_birimi_id:
            try:
                tl = ParaBirimi.objects.get(kod='TL')
                self.para_birimi = tl
            except:
                pass
        
        super().save(*args, **kwargs)


class StokGrupFiyat(BaseModel):
    stok = models.ForeignKey(StokKart, on_delete=models.CASCADE, related_name='grup_fiyatlari')
    cari_grup = models.ForeignKey(CariGrup, on_delete=models.CASCADE, related_name='stok_fiyatlari')
    satis_fiyati = models.DecimalField(max_digits=15, decimal_places=2, 
                                       verbose_name='Özel Satış Fiyatı', validators=[MinValueValidator(0)])
    
    class Meta:
        db_table = 'stok_grup_fiyatlari'
        verbose_name = 'Stok Grup Fiyatı'
        verbose_name_plural = 'Stok Grup Fiyatları'
        unique_together = [['stok', 'cari_grup']]
    
    def __str__(self):
        return f"{self.stok} - {self.cari_grup} : {self.satis_fiyati}"




class GenelStokSecenek(BaseModel):
    baslik = models.CharField(max_length=100, unique=True, verbose_name='Seçenek Başlığı')
    sira = models.IntegerField(default=0, verbose_name='Sıra')
    
    class Meta:
        db_table = 'genel_stok_secenekler'
        verbose_name = 'Genel Stok Seçeneği'
        verbose_name_plural = 'Genel Stok Seçenekleri'
        ordering = ['sira', 'baslik']
    
    def __str__(self):
        return self.baslik


class GenelStokSecenekDeger(BaseModel):
    FIYAT_TIPI = [
        ('sabit', 'Sabit Tutar'),
        ('yuzde', 'Yüzde'),
    ]
    
    secenek = models.ForeignKey(GenelStokSecenek, on_delete=models.CASCADE, related_name='degerler')
    deger = models.CharField(max_length=100, verbose_name='Değer')
    fiyat_tipi = models.CharField(max_length=10, choices=FIYAT_TIPI, default='sabit', verbose_name='Fiyat Tipi')
    fiyat_degeri = models.DecimalField(max_digits=15, decimal_places=2, default=0, 
                                       verbose_name='Fiyat Değeri')
    sira = models.IntegerField(default=0, verbose_name='Sıra')
    varsayilan = models.BooleanField(default=False, verbose_name='Varsayılan')
    
    class Meta:
        db_table = 'genel_stok_secenek_degerleri'
        verbose_name = 'Genel Seçenek Değeri'
        verbose_name_plural = 'Genel Seçenek Değerleri'
        ordering = ['sira', 'deger']
    
    def save(self, *args, **kwargs):
        # Eğer bu değer varsayılan olarak işaretlendiyse, aynı seçenekteki diğer varsayılanları kaldır
        if self.varsayilan:
            GenelStokSecenekDeger.objects.filter(
                secenek=self.secenek,
                varsayilan=True
            ).exclude(pk=self.pk).update(varsayilan=False)
        super().save(*args, **kwargs)




# Stok seçenekleri için modeller
class StokSecenek(BaseModel):
    stok = models.ForeignKey(StokKart, on_delete=models.CASCADE, related_name='secenekler')
    baslik = models.CharField(max_length=100, verbose_name='Seçenek Başlığı')
    sira = models.IntegerField(default=0, verbose_name='Sıra')
    
    class Meta:
        db_table = 'stok_secenekler'
        verbose_name = 'Stok Seçeneği'
        verbose_name_plural = 'Stok Seçenekleri'
        ordering = ['sira', 'baslik']
    
    def __str__(self):
        return f"{self.stok.ad} - {self.baslik}"


class StokSecenekDeger(BaseModel):
    FIYAT_TIPI = [
        ('sabit', 'Sabit Tutar'),
        ('yuzde', 'Yüzde'),
    ]
    
    secenek = models.ForeignKey(StokSecenek, on_delete=models.CASCADE, related_name='degerler')
    deger = models.CharField(max_length=100, verbose_name='Değer')
    fiyat_tipi = models.CharField(max_length=10, choices=FIYAT_TIPI, default='sabit', verbose_name='Fiyat Tipi')
    fiyat_degeri = models.DecimalField(max_digits=15, decimal_places=2, default=0, 
                                       verbose_name='Fiyat Değeri')  # Pozitif veya negatif olabilir
    sira = models.IntegerField(default=0, verbose_name='Sıra')
    varsayilan = models.BooleanField(default=False, verbose_name='Varsayılan')
    
    class Meta:
        db_table = 'stok_secenek_degerleri'
        verbose_name = 'Seçenek Değeri'
        verbose_name_plural = 'Seçenek Değerleri'
        ordering = ['sira', 'deger']


    def save(self, *args, **kwargs):
        # Eğer bu değer varsayılan olarak işaretlendiyse, aynı seçenekteki diğer varsayılanları kaldır
        if self.varsayilan:
            StokSecenekDeger.objects.filter(
                secenek=self.secenek,
                varsayilan=True
            ).exclude(pk=self.pk).update(varsayilan=False)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.secenek.baslik} - {self.deger}"
    
    def get_fiyat_etkisi(self, base_fiyat):
        """Temel fiyata göre bu seçeneğin fiyat etkisini hesapla"""
        if self.fiyat_tipi == 'sabit':
            return self.fiyat_degeri
        else:  # yuzde
            return base_fiyat * self.fiyat_degeri / Decimal('100')


# ===================== FATURA MODELLER =====================

class Fatura(BaseModel):
    FATURA_TIPLERI = [
        ('satis', 'Satış Faturası'),
        ('alis', 'Alış Faturası'),
    ]
    
    ISKONTO_TIPLERI = [
        ('yuzde', 'Yüzde'),
        ('tutar', 'Sabit Tutar'),
    ]
    
    fatura_no = models.CharField(max_length=20, unique=True, verbose_name='Fatura No')
    tarih = models.DateTimeField(default=timezone.now, verbose_name='Fatura Tarihi')  # DateTimeField olarak değiştir
    tip = models.CharField(max_length=20, choices=FATURA_TIPLERI, verbose_name='Fatura Tipi')
    
    # Cari Bilgisi
    cari = models.ForeignKey(CariKart, on_delete=models.PROTECT, related_name='faturalar', verbose_name='Cari')
    
    # İskonto Bilgileri
    iskonto_tipi = models.CharField(max_length=10, choices=ISKONTO_TIPLERI, null=True, blank=True, verbose_name='İskonto Tipi')
    iskonto_degeri = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='İskonto Değeri')
    iskonto_tutari = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='İskonto Tutarı')
    
    # Tutarlar
    ara_toplam = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Ara Toplam')
    kdv_tutari = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='KDV Tutarı')
    genel_toplam = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Genel Toplam')
    
    # Ek Bilgiler
    aciklama = models.TextField(blank=True, verbose_name='Açıklama')
    vade_tarihi = models.DateField(blank=True, null=True, verbose_name='Vade Tarihi')
    odendi = models.BooleanField(default=False, verbose_name='Ödendi')
    
    # Sistem
    iptal = models.BooleanField(default=False, verbose_name='İptal')
    olusturan = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Oluşturan')
    
    class Meta:
        db_table = 'faturalar'
        verbose_name = 'Fatura'
        verbose_name_plural = 'Faturalar'
        ordering = ['-tarih', '-fatura_no']
    
    def __str__(self):
        return f"{self.fatura_no} - {self.cari.unvan}"
    
    def save(self, *args, **kwargs):
        if not self.fatura_no:
            # Otomatik fatura no oluştur
            prefix = 'SF' if self.tip == 'satis' else 'AF'
            yil = timezone.now().year
            
            # Bu yılın son fatura numarasını bul
            last_fatura = Fatura.objects.filter(
                fatura_no__startswith=f"{prefix}{yil}"
            ).order_by('-fatura_no').first()
            
            if last_fatura:
                last_number = int(last_fatura.fatura_no[-6:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.fatura_no = f"{prefix}{yil}{new_number:06d}"
        
        super().save(*args, **kwargs)


class FaturaKalem(BaseModel):
    fatura = models.ForeignKey(Fatura, on_delete=models.CASCADE, related_name='kalemler', verbose_name='Fatura')
    stok = models.ForeignKey(StokKart, on_delete=models.PROTECT, verbose_name='Stok')
    
    miktar = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Miktar', 
                                validators=[MinValueValidator(0.01)])
    birim_fiyat = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Birim Fiyat', 
                                     validators=[MinValueValidator(0)])
    kdv_orani = models.IntegerField(default=20, verbose_name='KDV %')
    
    # İndirim bilgileri
    indirim_orani = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='İndirim %')
    indirim_tutari = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='İndirim Tutarı')
    indirim_aciklama = models.CharField(max_length=200, blank=True, verbose_name='İndirim Açıklama')
    
    # Hesaplanan alanlar
    tutar = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Tutar')
    kdv_tutari = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='KDV Tutarı')
    toplam_tutar = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Toplam Tutar')

    # KDV durumu için yeni alan ekle
    kdv_durumu = models.CharField(
        max_length=10, 
        choices=[('dahil', 'KDV Dahil'), ('haric', 'KDV Hariç')],
        default='dahil',
        verbose_name='KDV Durumu'
    )
    
    # Seçenekler için JSON field
    secenekler = models.JSONField(default=dict, blank=True, verbose_name='Seçenekler')
    secenek_fiyat_farki = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Seçenek Fiyat Farkı')
    
    class Meta:
        db_table = 'fatura_kalemleri'
        verbose_name = 'Fatura Kalemi'
        verbose_name_plural = 'Fatura Kalemleri'
    
    def hesapla(self):
        """Satır tutarlarını hesapla"""
        # Temel tutar (miktar * birim fiyat + seçenek farkı)
        base_tutar = self.miktar * (self.birim_fiyat + self.secenek_fiyat_farki)
        
        # İndirim hesapla
        if self.indirim_orani > 0:
            self.indirim_tutari = base_tutar * Decimal(self.indirim_orani) / Decimal(100)
        else:
            self.indirim_tutari = Decimal('0')
        
        # İndirimli tutar
        indirimli_tutar = base_tutar - self.indirim_tutari
        
        if self.kdv_durumu == 'dahil':
            # KDV dahilse - Toplam tutar sabit, KDV'yi içeriden hesapla
            self.toplam_tutar = indirimli_tutar  # Görünen fiyat (KDV dahil)
            
            # KDV'yi içeriden hesapla
            kdv_orani_katsayi = Decimal(100) + Decimal(self.kdv_orani)
            self.kdv_tutari = (indirimli_tutar * Decimal(self.kdv_orani)) / kdv_orani_katsayi
            
            # Net tutar (KDV hariç)
            self.tutar = indirimli_tutar - self.kdv_tutari
        else:
            # KDV hariçse - Net tutar sabit, KDV'yi üzerine ekle
            self.tutar = indirimli_tutar  # Net tutar (KDV hariç)
            self.kdv_tutari = indirimli_tutar * Decimal(self.kdv_orani) / Decimal(100)
            self.toplam_tutar = indirimli_tutar + self.kdv_tutari  # Toplam (KDV dahil)
    
    def save(self, *args, **kwargs):
        self.hesapla()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.fatura.fatura_no} - {self.stok.ad}"


# ===================== HAREKET MODELLER =====================

class KasaHareket(BaseModel):
    HAREKET_TIPLERI = [
        ('giris', 'Giriş'),
        ('cikis', 'Çıkış'),
    ]
    
    kasa = models.ForeignKey(Kasa, on_delete=models.PROTECT, related_name='hareketler', verbose_name='Kasa')
    tarih = models.DateTimeField(default=timezone.now, verbose_name='Tarih')
    tip = models.CharField(max_length=10, choices=HAREKET_TIPLERI, verbose_name='Hareket Tipi')
    
    tutar = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Tutar', 
                               validators=[MinValueValidator(0.01)])
    aciklama = models.CharField(max_length=200, verbose_name='Açıklama')
    
    # İlişkili kayıtlar
    cari = models.ForeignKey(CariKart, on_delete=models.PROTECT, blank=True, null=True, 
                            related_name='kasa_hareketleri', verbose_name='Cari')
    fatura = models.ForeignKey(Fatura, on_delete=models.PROTECT, blank=True, null=True, 
                              related_name='kasa_hareketleri', verbose_name='Fatura')
    
    # Sistem
    olusturan = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Oluşturan')
    
    class Meta:
        db_table = 'kasa_hareketleri'
        verbose_name = 'Kasa Hareketi'
        verbose_name_plural = 'Kasa Hareketleri'
        ordering = ['-tarih']
    
    def __str__(self):
        return f"{self.kasa.ad} - {self.get_tip_display()} - {self.tutar}"


class CariHareket(BaseModel):
    ISLEM_TIPLERI = [
        ('nakit', 'Nakit'),
        ('banka', 'Banka'),
        ('pos', 'POS'),
        ('virman', 'Virman'),
        ('diger', 'Diğer'),
    ]
    
    HAREKET_YONU = [
        ('giris', 'Giriş'),
        ('cikis', 'Çıkış'),
    ]
    
    # Temel bilgiler
    tarih = models.DateTimeField(default=timezone.now, verbose_name='İşlem Tarihi')
    cari = models.ForeignKey(CariKart, on_delete=models.PROTECT, 
                            related_name='hareketler', verbose_name='Cari')
    
    # Tutar bilgileri
    para_birimi = models.ForeignKey(ParaBirimi, on_delete=models.PROTECT, verbose_name='Para Birimi')
    tutar = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Tutar', 
                               validators=[MinValueValidator(0.01)])
    hareket_yonu = models.CharField(max_length=10, choices=HAREKET_YONU, verbose_name='Hareket Yönü')
    
    # Döviz işlemleri için
    doviz_kuru = models.DecimalField(
        max_digits=15, decimal_places=4, 
        null=True, blank=True, 
        verbose_name='Döviz Kuru'
    )
    tl_karsiligi = models.DecimalField(
        max_digits=15, decimal_places=2, 
        null=True, blank=True, 
        verbose_name='TL Karşılığı'
    )
    
    # İşlem bilgileri
    islem_tipi = models.CharField(max_length=10, choices=ISLEM_TIPLERI, verbose_name='İşlem Tipi')
    kasa = models.ForeignKey(Kasa, on_delete=models.PROTECT, null=True, blank=True, 
                            related_name='cari_hareketleri', verbose_name='Kasa')
    banka = models.ForeignKey(Banka, on_delete=models.PROTECT, null=True, blank=True, 
                             related_name='cari_hareketleri', verbose_name='Banka')
    pos = models.ForeignKey(Pos, on_delete=models.PROTECT, null=True, blank=True, 
                           related_name='cari_hareketleri', verbose_name='POS')
    
    # Açıklama
    aciklama = models.TextField(blank=True, verbose_name='Açıklama')
    
    # Sistem
    olusturan = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Oluşturan')
    
    class Meta:
        db_table = 'cari_hareketler'
        verbose_name = 'Cari Hareket'
        verbose_name_plural = 'Cari Hareketler'
        ordering = ['-tarih', '-id']
    
    def __str__(self):
        return f"{self.cari.unvan} - {self.get_hareket_yonu_display()} - {self.tutar} {self.para_birimi.kod}"
    
    @property
    def gercek_tutar(self):
        """Kasa/Banka için kullanılacak tutar"""
        # Eğer döviz işlemi varsa ve TL karşılığı varsa
        if self.doviz_kuru and self.tl_karsiligi and self.para_birimi.kod != 'TL':
            return self.tl_karsiligi  # TL tutarını döndür
        return self.tutar  # Normal tutarı döndür
    
    def save(self, *args, **kwargs):
        # Basit save - bakiye hesaplaması otomatik property'den gelecek
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Basit delete - bakiye hesaplaması otomatik property'den gelecek
        super().delete(*args, **kwargs)