from django import forms
from django.utils import timezone
from .models import (
    CariKart, CariGrup, Il, Ilce, StokKart, KasaHareket, Fatura,
    ParaBirimi, Kasa, Banka, Pos, CariHareket
)
from django import forms
from .models import CariKart, CariGrup, Il, Ilce, StokKart, KasaHareket, Fatura

class CariGrupForm(forms.ModelForm):
    class Meta:
        model = CariGrup
        fields = ['ad', 'ust_grup']  # 'kod' çıkarıldı
        widgets = {
            'ad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Grup adı giriniz'}),
            'ust_grup': forms.Select(attrs={'class': 'form-control'}),
        }

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
        fields = ['kod', 'ad', 'barkod', 'birim', 'kritik_stok', 
                  'alis_fiyati', 'satis_fiyati', 'kdv_orani']
        widgets = {
            'kod': forms.TextInput(attrs={'class': 'form-control'}),
            'ad': forms.TextInput(attrs={'class': 'form-control'}),
            'barkod': forms.TextInput(attrs={'class': 'form-control'}),
            'birim': forms.Select(attrs={'class': 'form-control'}),
            'kritik_stok': forms.NumberInput(attrs={'class': 'form-control'}),
            'alis_fiyati': forms.NumberInput(attrs={'class': 'form-control'}),
            'satis_fiyati': forms.NumberInput(attrs={'class': 'form-control'}),
            'kdv_orani': forms.NumberInput(attrs={'class': 'form-control'}),
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
            'step': '0.01'
        })
    )
    
    cikis = forms.DecimalField(
        required=False,
        min_value=0.01,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        })
    )
    
    class Meta:
        model = CariHareket
        fields = ['tarih', 'cari', 'para_birimi', 'islem_tipi', 'kasa', 'banka', 'pos', 'aciklama']
        widgets = {
            'tarih': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'cari': forms.Select(attrs={'class': 'form-control select2'}),
            'para_birimi': forms.Select(attrs={'class': 'form-control'}),
            'islem_tipi': forms.Select(attrs={'class': 'form-control'}),
            'kasa': forms.Select(attrs={'class': 'form-control'}),
            'banka': forms.Select(attrs={'class': 'form-control'}),
            'pos': forms.Select(attrs={'class': 'form-control'}),
            'aciklama': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['para_birimi'].queryset = ParaBirimi.objects.filter(silindi=False, aktif=True)
        self.fields['cari'].queryset = CariKart.objects.filter(silindi=False, aktif=True)
        self.fields['kasa'].queryset = Kasa.objects.filter(silindi=False, aktif=True)
        self.fields['banka'].queryset = Banka.objects.filter(silindi=False, aktif=True)
        self.fields['pos'].queryset = Pos.objects.filter(silindi=False, aktif=True)
        
        # Tarih alanı için varsayılan değer
        if not self.instance.pk:
            self.fields['tarih'].initial = timezone.now()
    
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
        
        # İşlem tipine göre kontroller
        if islem_tipi == 'nakit' and not cleaned_data.get('kasa'):
            raise forms.ValidationError('Nakit işlem için kasa seçmelisiniz.')
        elif islem_tipi == 'banka' and not cleaned_data.get('banka'):
            raise forms.ValidationError('Banka işlemi için banka seçmelisiniz.')
        elif islem_tipi == 'pos' and not cleaned_data.get('pos'):
            raise forms.ValidationError('POS işlemi için POS seçmelisiniz.')
        
        # Model için değerleri ayarla
        if giris:
            cleaned_data['tutar'] = giris
            cleaned_data['hareket_yonu'] = 'giris'
        else:
            cleaned_data['tutar'] = cikis
            cleaned_data['hareket_yonu'] = 'cikis'
        
        return cleaned_data