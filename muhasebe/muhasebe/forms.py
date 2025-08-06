from django import forms
from django.utils import timezone
# forms.py başına eklenecek
from .models import (
    CariKart, CariGrup, StokGrup, Il, Ilce, StokKart, KasaHareket, Fatura,
    ParaBirimi, Kasa, Banka, Pos, CariHareket,
    StokGrupFiyat, StokSecenek, StokSecenekDeger  # Bunları ekleyin
)

class CariGrupForm(forms.ModelForm):
    class Meta:
        model = CariGrup
        fields = ['ad', 'ust_grup']  # 'kod' çıkarıldı
        widgets = {
            'ad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Grup adı giriniz'}),
            'ust_grup': forms.Select(attrs={'class': 'form-control'}),
        }


class StokGrupForm(forms.ModelForm):
    class Meta:
        model = StokGrup
        fields = ['ad', 'ust_grup']  # 'kod' otomatik oluşturulacak
        widgets = {
            'ad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Grup adı giriniz'}),
            'ust_grup': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Üst grupları alfabetik sırala
        self.fields['ust_grup'].queryset = StokGrup.objects.filter(silindi=False).order_by('ad')
        self.fields['ust_grup'].required = False

class CariForm(forms.ModelForm):
    class Meta:
        model = CariKart
        fields = ['unvan', 'grup', 'yetkili_adi', 'yetkili_tel1', 'yetkili_tel2', 
                  'yetkili_tel3', 'telefon', 'email', 'adres', 'il', 'ilce', 
                  'firma_tipi', 'tc_kimlik', 'sirket_unvani', 'vergi_no', 'vergi_dairesi', 'risk_limiti', 'notlar', 'aktif']
        widgets = {
            'unvan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Firma/Kişi Ünvanı', 'required': True}),
            'grup': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'yetkili_adi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ad Soyad', 'required': True}),
            'yetkili_tel1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0555 555 5555'}),
            'yetkili_tel2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0555 555 5555'}),
            'yetkili_tel3': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0555 555 5555'}),
            'telefon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0555 555 5555', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ornek@email.com'}),
            'adres': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': True}),
            'il': forms.Select(attrs={'class': 'form-control', 'id': 'il_select', 'required': True}),
            'ilce': forms.Select(attrs={'class': 'form-control', 'id': 'ilce_select', 'required': True}),
            'firma_tipi': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'tc_kimlik': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12345678901', 'maxlength': '11'}),
            'sirket_unvani': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Şirket Ünvanı'}),
            'vergi_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234567890', 'maxlength': '11'}),
            'vergi_dairesi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vergi Dairesi'}),
            'risk_limiti': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'notlar': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Özel notlarınızı buraya yazabilirsiniz...'}),
            'aktif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # İlçe seçimini başlangıçta boş yap
        self.fields['ilce'].queryset = Ilce.objects.none()
        
        # Grupları alfabetik sırala
        self.fields['grup'].queryset = CariGrup.objects.filter(silindi=False).order_by('ad')
        
        # İlleri plaka koduna göre sırala
        self.fields['il'].queryset = Il.objects.all().order_by('plaka')
        
        if 'il' in self.data:
            try:
                il_id = int(self.data.get('il'))
                self.fields['ilce'].queryset = Ilce.objects.filter(il_id=il_id).order_by('ad')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.il:
            self.fields['ilce'].queryset = self.instance.il.ilceler.order_by('ad')
    
    def clean(self):
        cleaned_data = super().clean()
        firma_tipi = cleaned_data.get('firma_tipi')
        
        if firma_tipi == 'sahis':
            # Şahıs firması için TC kimlik zorunlu
            if not cleaned_data.get('tc_kimlik'):
                self.add_error('tc_kimlik', 'Şahıs firması için TC Kimlik No zorunludur.')
        elif firma_tipi == 'sirket':
            # Şirket için şirket ünvanı ve vergi no zorunlu
            if not cleaned_data.get('sirket_unvani'):
                self.add_error('sirket_unvani', 'Şirket için Şirket Ünvanı zorunludur.')
            if not cleaned_data.get('vergi_no'):
                self.add_error('vergi_no', 'Şirket için Vergi No zorunludur.')
        
        return cleaned_data

class StokForm(forms.ModelForm):
    class Meta:
        model = StokKart
        fields = ['ad', 'barkod', 'birim', 'para_birimi', 'kritik_stok', 'miktar',
                  'alis_fiyati', 'satis_fiyati', 'kdv_orani', 'grup', 'aktif']  # 'miktar' ekledik
        widgets = {
            'ad': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'barkod': forms.TextInput(attrs={'class': 'form-control'}),
            'birim': forms.Select(attrs={'class': 'form-control'}),
            'para_birimi': forms.Select(attrs={'class': 'form-control'}),
            'grup': forms.Select(attrs={'class': 'form-control'}),
            'kritik_stok': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'miktar': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),  # YENİ
            'alis_fiyati': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'satis_fiyati': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'kdv_orani': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
            'aktif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        # User bilgisini al
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
        # Para birimlerini aktif olanlarla sınırla
        self.fields['para_birimi'].queryset = ParaBirimi.objects.filter(silindi=False, aktif=True)
    
        # Stok gruplarını aktif olanlarla sınırla ve alfabetik sırala
        self.fields['grup'].queryset = StokGrup.objects.filter(silindi=False, aktif=True).order_by('ad')
        self.fields['grup'].required = False
    
        # Miktar alanı yetkisi kontrolü
        if self.user and not self.user.is_superuser:  # user yerine self.user kullan
            # Superuser değilse miktar alanını devre dışı bırak
            self.fields['miktar'].widget.attrs['readonly'] = True
            self.fields['miktar'].widget.attrs['class'] += ' bg-light'
            self.fields['miktar'].help_text = 'Bu alanı sadece yöneticiler düzenleyebilir'

    def clean_miktar(self):
        miktar = self.cleaned_data.get('miktar')
    
        # Eğer user bilgisi varsa ve superuser değilse
        if hasattr(self, 'initial') and self.initial.get('miktar') is not None:
            # Düzenleme modunda
            if hasattr(self, 'user') and self.user and not self.user.is_superuser:
                # Eski değeri döndür (değişikliğe izin verme)
                return self.initial.get('miktar')
    
        return miktar

    def clean_ad(self):
        ad = self.cleaned_data.get('ad')
    
        # Mevcut stok güncelleniyorsa, kendisi hariç kontrol et
        if self.instance.pk:
            # Aktif kayıtlarda kontrol
            exists_active = StokKart.objects.filter(
                ad__iexact=ad,
                silindi=False
            ).exclude(pk=self.instance.pk).exists()
        
            # Silinmiş kayıtlarda kontrol
            exists_deleted = StokKart.objects.filter(
                ad__iexact=ad,
                silindi=True
            ).exists()
        else:
            # Yeni stok ekleniyor
            exists_active = StokKart.objects.filter(
                ad__iexact=ad,
                silindi=False
            ).exists()
        
            exists_deleted = StokKart.objects.filter(
                ad__iexact=ad,
                silindi=True
            ).exists()
    
        if exists_active:
            raise forms.ValidationError('Bu isimde bir stok zaten mevcut!')
    
        if exists_deleted:
            raise forms.ValidationError('Bu isimde silinmiş bir stok bulunmaktadır. Lütfen farklı bir isim kullanın veya silinmiş kaydı kalıcı olarak silin!')
    
        return ad
    
    def clean(self):
        cleaned_data = super().clean()
        alis_fiyati = cleaned_data.get('alis_fiyati', 0) or 0
        satis_fiyati = cleaned_data.get('satis_fiyati', 0) or 0
        
        if alis_fiyati > satis_fiyati and satis_fiyati > 0:
            self.add_error('satis_fiyati', 'Satış fiyatı alış fiyatından düşük olamaz!')
        
        return cleaned_data

class StokGrupFiyatForm(forms.ModelForm):
    class Meta:
        model = StokGrupFiyat
        fields = ['cari_grup', 'satis_fiyati']
        widgets = {
            'cari_grup': forms.Select(attrs={'class': 'form-control'}),
            'satis_fiyati': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cari_grup'].queryset = CariGrup.objects.filter(silindi=False, aktif=True)

class StokSecenekForm(forms.ModelForm):
    class Meta:
        model = StokSecenek
        fields = ['baslik', 'sira']
        widgets = {
            'baslik': forms.TextInput(attrs={'class': 'form-control'}),
            'sira': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class StokSecenekDegerForm(forms.ModelForm):
    class Meta:
        model = StokSecenekDeger
        fields = ['deger', 'fiyat_tipi', 'fiyat_degeri', 'sira']
        widgets = {
            'deger': forms.TextInput(attrs={'class': 'form-control'}),
            'fiyat_tipi': forms.Select(attrs={'class': 'form-control'}),
            'fiyat_degeri': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sira': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class KasaHareketForm(forms.ModelForm):
    class Meta:
        model = KasaHareket
        fields = ['kasa', 'tip', 'tutar', 'aciklama', 'cari']
        widgets = {
            'kasa': forms.Select(attrs={'class': 'form-control'}),
            'tip': forms.Select(attrs={'class': 'form-control'}),
            'tutar': forms.NumberInput(attrs={'class': 'form-control'}),
            'aciklama': forms.TextInput(attrs={'class': 'form-control'}),
            'cari': forms.Select(attrs={'class': 'form-control'}),
        }


class ParaBirimiForm(forms.ModelForm):
    class Meta:
        model = ParaBirimi
        fields = ['kod', 'ad', 'sembol', 'aktif']
        widgets = {
            'kod': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'TRY, USD, EUR'}),
            'ad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Türk Lirası'}),
            'sembol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '₺, $, €'}),
            'aktif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class KasaForm(forms.ModelForm):
    class Meta:
        model = Kasa
        fields = ['kod', 'ad', 'para_birimi', 'aktif']
        widgets = {
            'kod': forms.TextInput(attrs={'class': 'form-control'}),
            'ad': forms.TextInput(attrs={'class': 'form-control'}),
            'para_birimi': forms.Select(attrs={'class': 'form-control'}),
            'aktif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['para_birimi'].queryset = ParaBirimi.objects.filter(silindi=False, aktif=True)


class BankaForm(forms.ModelForm):
    class Meta:
        model = Banka
        fields = ['kod', 'ad', 'sube', 'hesap_no', 'iban', 'para_birimi', 'aktif']
        widgets = {
            'kod': forms.TextInput(attrs={'class': 'form-control'}),
            'ad': forms.TextInput(attrs={'class': 'form-control'}),
            'sube': forms.TextInput(attrs={'class': 'form-control'}),
            'hesap_no': forms.TextInput(attrs={'class': 'form-control'}),
            'iban': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'TR000000000000000000000000'}),
            'para_birimi': forms.Select(attrs={'class': 'form-control'}),
            'aktif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['para_birimi'].queryset = ParaBirimi.objects.filter(silindi=False, aktif=True)


class PosForm(forms.ModelForm):
    class Meta:
        model = Pos
        fields = ['kod', 'ad', 'banka', 'komisyon_orani', 'aktif']
        widgets = {
            'kod': forms.TextInput(attrs={'class': 'form-control'}),
            'ad': forms.TextInput(attrs={'class': 'form-control'}),
            'banka': forms.Select(attrs={'class': 'form-control'}),
            'komisyon_orani': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aktif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['banka'].queryset = Banka.objects.filter(silindi=False, aktif=True)


class CariHareketForm(forms.ModelForm):
    giris = forms.DecimalField(
        required=False,
        min_value=0.01,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0.01'  
        })
    )
    
    cikis = forms.DecimalField(
        required=False,
        min_value=0.01,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0.01'  
        })
    )
    
    class Meta:
        model = CariHareket
        fields = ['tarih', 'cari', 'para_birimi', 'islem_tipi', 'kasa', 'banka', 'pos', 'aciklama']
        widgets = {
            'tarih': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True
            }),
            'cari': forms.Select(attrs={'class': 'form-control select2', 'required': True}),
            'para_birimi': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'islem_tipi': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'kasa': forms.Select(attrs={'class': 'form-control'}),
            'banka': forms.Select(attrs={'class': 'form-control'}),
            'pos': forms.Select(attrs={'class': 'form-control'}),
            'aciklama': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Varsayılan para birimi TL
        try:
            tl = ParaBirimi.objects.get(kod='TL', silindi=False, aktif=True)
            self.fields['para_birimi'].initial = tl.id
        except:
            pass

        if not self.instance.pk:  # Sadece yeni kayıtlarda
            self.fields['islem_tipi'].initial = 'nakit'

        # Düzenleme modunda ise, tutar değerlerini ayarla
        if self.instance and self.instance.pk:
            if self.instance.hareket_yonu == 'giris':
                self.initial['giris'] = self.instance.tutar
                self.initial['cikis'] = None
            elif self.instance.hareket_yonu == 'cikis':
                self.initial['cikis'] = self.instance.tutar
                self.initial['giris'] = None
            
        self.fields['para_birimi'].queryset = ParaBirimi.objects.filter(silindi=False, aktif=True)
        self.fields['cari'].queryset = CariKart.objects.filter(silindi=False, aktif=True)
        self.fields['kasa'].queryset = Kasa.objects.filter(silindi=False, aktif=True)
        self.fields['banka'].queryset = Banka.objects.filter(silindi=False, aktif=True)
        self.fields['pos'].queryset = Pos.objects.filter(silindi=False, aktif=True)
        
        # Kasa, banka, pos alanlarını opsiyonel yap
        self.fields['kasa'].required = False
        self.fields['banka'].required = False
        self.fields['pos'].required = False
        
        # Tarih alanı için varsayılan değer
        if not self.instance.pk:
            # Şu anki tarih ve saati datetime-local formatında ayarla
            now = timezone.now()
            self.fields['tarih'].initial = now.strftime('%Y-%m-%dT%H:%M')

        if self.instance and self.instance.pk and self.instance.tarih:
            # Düzenleme modunda - timezone'u dikkate al
            local_time = timezone.localtime(self.instance.tarih)
            self.initial['tarih'] = local_time.strftime('%Y-%m-%dT%H:%M')
        elif not self.instance.pk:
            # Yeni kayıt
            local_time = timezone.localtime(timezone.now())
            self.initial['tarih'] = local_time.strftime('%Y-%m-%dT%H:%M')
    
    def clean(self):
        cleaned_data = super().clean()
        giris = cleaned_data.get('giris')
        cikis = cleaned_data.get('cikis')
        islem_tipi = cleaned_data.get('islem_tipi')
        
        # Giriş veya çıkış tutarından en az biri dolu olmalı
        if not giris and not cikis:
            raise forms.ValidationError('Giriş veya çıkış tutarından birini girmelisiniz.')
        
        # İkisi birden dolu olamaz
        if giris and cikis:
            raise forms.ValidationError('Hem giriş hem çıkış tutarı girilemez.')
        
        # Tutar 0 veya negatif olamaz
        if giris is not None and giris <= 0:
            self.add_error('giris', 'Giriş tutarı 0 veya negatif olamaz.')
        
        if cikis is not None and cikis <= 0:
            self.add_error('cikis', 'Çıkış tutarı 0 veya negatif olamaz.')
        
        # İşlem tipine göre kontroller
        if islem_tipi == 'nakit' and not cleaned_data.get('kasa'):
            raise forms.ValidationError('Nakit işlem için kasa seçmelisiniz.')
        elif islem_tipi == 'banka' and not cleaned_data.get('banka'):
            raise forms.ValidationError('Banka işlemi için banka seçmelisiniz.')
        elif islem_tipi == 'pos' and not cleaned_data.get('pos'):
            raise forms.ValidationError('POS işlemi için POS seçmelisiniz.')
        
        # Model için değerleri ayarla - sadece geçerli değerler varsa
        if giris and giris > 0:
            cleaned_data['tutar'] = giris
            cleaned_data['hareket_yonu'] = 'giris'
        elif cikis and cikis > 0:
            cleaned_data['tutar'] = cikis
            cleaned_data['hareket_yonu'] = 'cikis'
        
        return cleaned_data
    
class CariVirmanForm(forms.Form):
    tarih = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local',
            'required': True
        }),
        initial=timezone.now
    )
    
    # Alıcı Cari
    gonderen_cari = forms.ModelChoiceField(
        queryset=CariKart.objects.filter(silindi=False, aktif=True),
        widget=forms.Select(attrs={'class': 'form-control select2', 'required': True}),
        label='Alıcı Cari'
    )
    
    gonderen_para_birimi = forms.ModelChoiceField(
        queryset=ParaBirimi.objects.filter(silindi=False, aktif=True),
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        label='Para Birimi'
    )
    
    gonderen_tutar = forms.DecimalField(
        min_value=0.01,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0.01'
        }),
        label='Tutar'
    )
    
    # Gönderen Cari
    alici_cari = forms.ModelChoiceField(
        queryset=CariKart.objects.filter(silindi=False, aktif=True),
        widget=forms.Select(attrs={'class': 'form-control select2', 'required': True}),
        label='Gönderen Cari'
    )
    
    alici_para_birimi = forms.ModelChoiceField(
        queryset=ParaBirimi.objects.filter(silindi=False, aktif=True),
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        label='Para Birimi'
    )
    
    alici_tutar = forms.DecimalField(
        min_value=0.01,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0.01'
        }),
        label='Tutar'
    )
    
    aciklama = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Virman açıklaması...'
        }),
        label='Açıklama'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Varsayılan para birimi TL
        try:
            tl = ParaBirimi.objects.get(kod='TL', silindi=False, aktif=True)
            self.fields['gonderen_para_birimi'].initial = tl.id
            self.fields['alici_para_birimi'].initial = tl.id
        except:
            pass
        
        # Tarih alanı için varsayılan değer
        local_time = timezone.localtime(timezone.now())
        self.initial['tarih'] = local_time.strftime('%Y-%m-%dT%H:%M')
    
    def clean(self):
        cleaned_data = super().clean()
        gonderen_cari = cleaned_data.get('gonderen_cari')
        alici_cari = cleaned_data.get('alici_cari')
        
        if gonderen_cari and alici_cari and gonderen_cari == alici_cari:
            raise forms.ValidationError('Gönderen ve alıcı cari aynı olamaz!')
        
        return cleaned_data
    

# forms.py'ye eklenecek

class FaturaForm(forms.ModelForm):
    class Meta:
        model = Fatura
        fields = ['tarih', 'tip', 'cari', 'iskonto_tipi', 'iskonto_degeri', 
                  'aciklama', 'vade_tarihi']
        widgets = {
            'tarih': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True
            }),
            'tip': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'cari': forms.Select(attrs={'class': 'form-control select2', 'required': True}),
            'iskonto_tipi': forms.Select(attrs={'class': 'form-control'}),
            'iskonto_degeri': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'aciklama': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'vade_tarihi': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Aktif carileri getir
        self.fields['cari'].queryset = CariKart.objects.filter(silindi=False, aktif=True)
        
        # Yeni fatura için varsayılan tarih
        if not self.instance.pk:
            local_time = timezone.localtime(timezone.now())
            self.initial['tarih'] = local_time.strftime('%Y-%m-%dT%H:%M')
            self.initial['tip'] = 'satis'  # Varsayılan satış faturası
        else:
            # Düzenleme modunda
            if self.instance.tarih:
                local_time = timezone.localtime(self.instance.tarih)
                self.initial['tarih'] = local_time.strftime('%Y-%m-%dT%H:%M')