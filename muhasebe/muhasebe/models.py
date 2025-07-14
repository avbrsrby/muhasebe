from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
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
    bakiye = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Bakiye')
    aktif = models.BooleanField(default=True, verbose_name='Aktif')
    
    class Meta:
        db_table = 'kasalar'
        verbose_name = 'Kasa'
        verbose_name_plural = 'Kasalar'
        ordering = ['kod']
    
    def __str__(self):
        return f"{self.kod} - {self.ad} ({self.para_birimi.kod})"


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
    bakiye = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Bakiye')
    aktif = models.BooleanField(default=True, verbose_name='Aktif')
    
    class Meta:
        db_table = 'bankalar'
        verbose_name = 'Banka'
        verbose_name_plural = 'Bankalar'
        ordering = ['kod']
    
    def __str__(self):
        return f"{self.kod} - {self.ad} ({self.para_birimi.kod})"


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
    
    # Mali Bilgiler
    bakiye = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Bakiye')
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
    
    kod = models.CharField(max_length=30, unique=True, verbose_name='Stok Kodu')
    ad = models.CharField(max_length=200, verbose_name='Stok Adı')
    barkod = models.CharField(max_length=20, blank=True, verbose_name='Barkod')
    
    # Birim ve Miktar
    birim = models.CharField(max_length=10, choices=BIRIMLER, default='ADET', verbose_name='Birim')
    miktar = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Mevcut Miktar')
    kritik_stok = models.DecimalField(max_digits=15, decimal_places=2, default=0, 
                                     verbose_name='Kritik Stok Seviyesi', validators=[MinValueValidator(0)])
    
    # Fiyatlar
    alis_fiyati = models.DecimalField(max_digits=15, decimal_places=2, default=0, 
                                     verbose_name='Alış Fiyatı', validators=[MinValueValidator(0)])
    satis_fiyati = models.DecimalField(max_digits=15, decimal_places=2, default=0, 
                                      verbose_name='Satış Fiyatı', validators=[MinValueValidator(0)])
    kdv_orani = models.IntegerField(default=18, verbose_name='KDV Oranı %')
    
    # Sistem
    aktif = models.BooleanField(default=True, verbose_name='Aktif')
    
    class Meta:
        db_table = 'stok_kartlar'
        verbose_name = 'Stok Kart'
        verbose_name_plural = 'Stok Kartlar'
        ordering = ['kod']
    
    def __str__(self):
        return f"{self.kod} - {self.ad}"


# ===================== FATURA MODELLER =====================

class Fatura(BaseModel):
    FATURA_TIPLERI = [
        ('alis', 'Alış Faturası'),
        ('satis', 'Satış Faturası'),
        ('iade_alis', 'Alış İade Faturası'),
        ('iade_satis', 'Satış İade Faturası'),
    ]
    
    fatura_no = models.CharField(max_length=20, unique=True, verbose_name='Fatura No')
    tarih = models.DateField(default=timezone.now, verbose_name='Fatura Tarihi')
    tip = models.CharField(max_length=20, choices=FATURA_TIPLERI, verbose_name='Fatura Tipi')
    
    # Cari Bilgisi
    cari = models.ForeignKey(CariKart, on_delete=models.PROTECT, related_name='faturalar', verbose_name='Cari')
    
    # Tutarlar
    ara_toplam = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Ara Toplam')
    kdv_tutari = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='KDV Tutarı')
    genel_toplam = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Genel Toplam')
    
    # Ödeme
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


class FaturaKalem(BaseModel):
    fatura = models.ForeignKey(Fatura, on_delete=models.CASCADE, related_name='kalemler', verbose_name='Fatura')
    stok = models.ForeignKey(StokKart, on_delete=models.PROTECT, verbose_name='Stok')
    
    miktar = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Miktar', 
                                validators=[MinValueValidator(0.01)])
    birim_fiyat = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Birim Fiyat', 
                                     validators=[MinValueValidator(0)])
    kdv_orani = models.IntegerField(default=18, verbose_name='KDV %')
    
    # Hesaplanan alanlar
    tutar = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Tutar')
    kdv_tutari = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='KDV Tutarı')
    toplam_tutar = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Toplam Tutar')
    
    class Meta:
        db_table = 'fatura_kalemleri'
        verbose_name = 'Fatura Kalemi'
        verbose_name_plural = 'Fatura Kalemleri'
    
    def save(self, *args, **kwargs):
        # Otomatik hesaplamalar
        self.tutar = self.miktar * self.birim_fiyat
        self.kdv_tutari = self.tutar * Decimal(self.kdv_orani) / Decimal(100)
        self.toplam_tutar = self.tutar + self.kdv_tutari
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
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Cari bakiyesini güncelle
        self.update_cari_bakiye()
        
        # İlgili kasa/banka/pos bakiyesini güncelle
        self.update_hesap_bakiye()
    
    def update_cari_bakiye(self):
        """Cari bakiyesini günceller"""
        # Bu basit bir örnek, gerçek uygulamada döviz çevrim hesaplaması gerekebilir
        if self.hareket_yonu == 'giris':
            # Bizden cariye giriş (cari borçlandı)
            self.cari.bakiye -= self.tutar
        else:
            # Cariden bize çıkış (cari alacaklandı)
            self.cari.bakiye += self.tutar
        self.cari.save()
    
    def update_hesap_bakiye(self):
        """İlgili kasa/banka bakiyesini günceller"""
        if self.islem_tipi == 'nakit' and self.kasa:
            if self.hareket_yonu == 'giris':
                self.kasa.bakiye += self.tutar
            else:
                self.kasa.bakiye -= self.tutar
            self.kasa.save()
        elif self.islem_tipi == 'banka' and self.banka:
            if self.hareket_yonu == 'giris':
                self.banka.bakiye += self.tutar
            else:
                self.banka.bakiye -= self.tutar
            self.banka.save()