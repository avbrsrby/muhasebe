from django.contrib import admin
from .models import CariKart, CariGrup, Il, Ilce, Kasa, Banka, StokKart, Fatura, FaturaKalem, KasaHareket, ParaBirimi, Pos, CariHareket

# Cari Admin
@admin.register(CariKart)
class CariKartAdmin(admin.ModelAdmin):
    list_display = ['kod', 'unvan', 'grup', 'firma_tipi', 'bakiye', 'aktif']  # tip yerine firma_tipi
    list_filter = ['firma_tipi', 'grup', 'aktif']  # tip yerine firma_tipi
    search_fields = ['kod', 'unvan', 'vergi_no', 'tc_kimlik']

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

# Stok Admin
@admin.register(StokKart)
class StokKartAdmin(admin.ModelAdmin):
    list_display = ['kod', 'ad', 'birim', 'miktar', 'satis_fiyati', 'aktif']
    list_filter = ['birim', 'aktif']
    search_fields = ['kod', 'ad', 'barkod']

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