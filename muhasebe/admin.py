# admin.py - tam güncel hali

from django.contrib import admin
from .models import (
    CariKart, CariGrup, StokGrup, Il, Ilce, Kasa, Banka, StokKart, Fatura, 
    FaturaKalem, KasaHareket, ParaBirimi, Pos, CariHareket,
    StokGrupFiyat, StokSecenek, StokSecenekDeger
)

# Cari Admin
@admin.register(CariKart)
class CariKartAdmin(admin.ModelAdmin):
    list_display = ['kod', 'unvan', 'grup', 'firma_tipi', 'bakiye', 'aktif']
    list_filter = ['firma_tipi', 'grup', 'aktif']
    search_fields = ['kod', 'unvan', 'vergi_no', 'tc_kimlik']

# Cari Grup Admin
@admin.register(CariGrup)
class CariGrupAdmin(admin.ModelAdmin):
    list_display = ['kod', 'ad', 'ust_grup', 'seviye', 'aktif']
    list_filter = ['aktif', 'seviye']
    search_fields = ['kod', 'ad']

# Stok Grup Admin
@admin.register(StokGrup)
class StokGrupAdmin(admin.ModelAdmin):
    list_display = ['kod', 'ad', 'ust_grup', 'seviye', 'aktif']
    list_filter = ['aktif', 'seviye']
    search_fields = ['kod', 'ad']

# Kasa Admin
@admin.register(Kasa)
class KasaAdmin(admin.ModelAdmin):
    list_display = ['kod', 'ad', 'para_birimi', 'bakiye', 'aktif']
    list_filter = ['para_birimi', 'aktif']
    search_fields = ['kod', 'ad']

# Banka Admin
@admin.register(Banka)
class BankaAdmin(admin.ModelAdmin):
    list_display = ['kod', 'ad', 'para_birimi', 'bakiye', 'aktif']
    list_filter = ['para_birimi', 'aktif']
    search_fields = ['kod', 'ad', 'iban']

# Pos Admin
@admin.register(Pos)
class PosAdmin(admin.ModelAdmin):
    list_display = ['kod', 'ad', 'banka', 'komisyon_orani', 'aktif']
    list_filter = ['banka', 'aktif']
    search_fields = ['kod', 'ad']

# Para Birimi Admin
@admin.register(ParaBirimi)
class ParaBirimiAdmin(admin.ModelAdmin):
    list_display = ['kod', 'ad', 'sembol', 'aktif']
    list_filter = ['aktif']
    search_fields = ['kod', 'ad']

# İl Admin
@admin.register(Il)
class IlAdmin(admin.ModelAdmin):
    list_display = ['plaka', 'ad']
    search_fields = ['ad']
    ordering = ['plaka']

# İlçe Admin
@admin.register(Ilce)
class IlceAdmin(admin.ModelAdmin):
    list_display = ['ad', 'il']
    list_filter = ['il']
    search_fields = ['ad', 'il__ad']
    ordering = ['il', 'ad']

# Stok Inline'ları
class StokGrupFiyatInline(admin.TabularInline):
    model = StokGrupFiyat
    extra = 0
    fields = ['cari_grup', 'satis_fiyati']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(silindi=False)

class StokSecenekDegerInline(admin.TabularInline):
    model = StokSecenekDeger
    extra = 1
    fields = ['deger', 'fiyat_tipi', 'fiyat_degeri', 'sira']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(silindi=False)

class StokSecenekInline(admin.TabularInline):
    model = StokSecenek
    extra = 0
    fields = ['baslik', 'sira']
    show_change_link = True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(silindi=False)

# Stok Admin
@admin.register(StokKart)
class StokKartAdmin(admin.ModelAdmin):
    list_display = ['kod', 'ad', 'birim', 'para_birimi', 'miktar', 'satis_fiyati', 'aktif']
    list_filter = ['birim', 'para_birimi', 'aktif']
    search_fields = ['kod', 'ad', 'barkod']
    readonly_fields = ['kod']
    inlines = [StokGrupFiyatInline, StokSecenekInline]

# Stok Seçenek Admin
@admin.register(StokSecenek)
class StokSecenekAdmin(admin.ModelAdmin):
    list_display = ['stok', 'baslik', 'sira']
    list_filter = ['stok']
    search_fields = ['stok__ad', 'baslik']
    inlines = [StokSecenekDegerInline]

# Stok Grup Fiyat Admin (opsiyonel)
@admin.register(StokGrupFiyat)
class StokGrupFiyatAdmin(admin.ModelAdmin):
    list_display = ['stok', 'cari_grup', 'satis_fiyati']
    list_filter = ['cari_grup']
    search_fields = ['stok__ad', 'cari_grup__ad']

# Fatura Inline
class FaturaKalemInline(admin.TabularInline):
    model = FaturaKalem
    extra = 1

# Fatura Admin
@admin.register(Fatura)
class FaturaAdmin(admin.ModelAdmin):
    list_display = ['fatura_no', 'tarih', 'tip', 'cari', 'genel_toplam', 'odendi']
    list_filter = ['tip', 'odendi', 'iptal']
    search_fields = ['fatura_no', 'cari__unvan']
    inlines = [FaturaKalemInline]

# Kasa Hareket Admin
@admin.register(KasaHareket)
class KasaHareketAdmin(admin.ModelAdmin):
    list_display = ['kasa', 'tarih', 'tip', 'tutar', 'cari', 'aciklama']
    list_filter = ['kasa', 'tip']
    date_hierarchy = 'tarih'

# Cari Hareket Admin
@admin.register(CariHareket)
class CariHareketAdmin(admin.ModelAdmin):
    list_display = ['tarih', 'cari', 'para_birimi', 'tutar', 'hareket_yonu', 'islem_tipi']
    list_filter = ['hareket_yonu', 'islem_tipi', 'para_birimi']
    search_fields = ['cari__unvan', 'aciklama']
    date_hierarchy = 'tarih'