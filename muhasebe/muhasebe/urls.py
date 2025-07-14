from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Login/Logout
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Ana sayfa (login sonrası)
    path('anasayfa/', views.anasayfa, name='anasayfa'),
    
    # Cari işlemler
    path('cari/', views.cari_list, name='cari_list'),
    path('cari/ekle/', views.cari_ekle, name='cari_ekle'),
    path('cari/<int:pk>/duzenle/', views.cari_duzenle, name='cari_duzenle'),
    
    # Cari grup işlemleri
    path('cari/grup/', views.cari_grup_list, name='cari_grup_list'),
    path('cari/grup/<int:pk>/duzenle/', views.cari_grup_duzenle, name='cari_grup_duzenle'),
    path('cari/grup/<int:pk>/sil/', views.cari_grup_sil, name='cari_grup_sil'),
    
    # AJAX
    path('ajax/ilceler/<int:il_id>/', views.get_ilceler, name='get_ilceler'),
    
    # Stok işlemler
    path('stok/', views.stok_list, name='stok_list'),
    path('stok/ekle/', views.stok_ekle, name='stok_ekle'),
    
    # Kasa işlemler
    path('kasa/', views.kasa_list, name='kasa_list'),
    path('kasa/hareket/', views.kasa_hareket, name='kasa_hareket'),
    
    # Fatura işlemler
    path('fatura/', views.fatura_list, name='fatura_list'),
    path('fatura/ekle/', views.fatura_ekle, name='fatura_ekle'),
   
    # Cari silme
    path('cari/<int:pk>/sil/', views.cari_sil, name='cari_sil'),
    path('cari/<int:pk>/', views.cari_detay, name='cari_detay'),

    # Silinen kayıtlar (sadece superuser)
    path('silinen-kayitlar/', views.silinen_kayitlar, name='silinen_kayitlar'),
    path('geri-yukle/<str:model_name>/<int:pk>/', views.kayit_geri_yukle, name='kayit_geri_yukle'),
    path('kalici-sil/<str:model_name>/<int:pk>/', views.kayit_kalici_sil, name='kayit_kalici_sil'),

    # Tümünü sil (sadece superuser)
    path('tumunu-kalici-sil/<str:kategori>/', views.tumunu_kalici_sil, name='tumunu_kalici_sil'),

    # Yetkili menüsü (sadece superuser)
    path('yetkili/', views.yetkili_menu, name='yetkili_menu'),
    path('yetkili/para-birimi/', views.para_birimi_list, name='para_birimi_list'),
    path('yetkili/para-birimi/ekle/', views.para_birimi_ekle, name='para_birimi_ekle'),
    path('yetkili/para-birimi/<int:pk>/duzenle/', views.para_birimi_duzenle, name='para_birimi_duzenle'),
    
    path('yetkili/kasa/', views.kasa_list, name='kasa_list'),
    path('yetkili/kasa/ekle/', views.kasa_ekle, name='kasa_ekle'),
    path('yetkili/kasa/<int:pk>/duzenle/', views.kasa_duzenle, name='kasa_duzenle'),
    
    path('yetkili/banka/', views.banka_list, name='banka_list'),
    path('yetkili/banka/ekle/', views.banka_ekle, name='banka_ekle'),
    path('yetkili/banka/<int:pk>/duzenle/', views.banka_duzenle, name='banka_duzenle'),
    
    path('yetkili/pos/', views.pos_list, name='pos_list'),
    path('yetkili/pos/ekle/', views.pos_ekle, name='pos_ekle'),
    path('yetkili/pos/<int:pk>/duzenle/', views.pos_duzenle, name='pos_duzenle'),
    
    # Cari hareket işlemleri
    path('cari-hareket/', views.cari_hareket_list, name='cari_hareket_list'),
    path('cari-hareket/ekle/', views.cari_hareket_ekle, name='cari_hareket_ekle'),
    path('cari/<int:cari_id>/hareketler/', views.cari_hareketler, name='cari_hareketler'),
    
    # AJAX
    path('ajax/cari-ara/', views.cari_ara, name='cari_ara'),
    path('ajax/kasa-banka-getir/', views.kasa_banka_getir, name='kasa_banka_getir'),

]