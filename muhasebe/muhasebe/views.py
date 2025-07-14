from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from .models import CariKart, CariGrup, Kasa, StokKart, Fatura, KasaHareket, Il, Ilce
from .forms import CariForm, CariGrupForm, StokForm, KasaHareketForm
from django.db.models import Q
from decimal import Decimal

# Model import'ları
from .models import (
    CariKart, CariGrup, Kasa, Banka, StokKart, Fatura, KasaHareket, 
    Il, Ilce, ParaBirimi, Pos, CariHareket
)

# Form import'ları  
from .forms import (
    CariForm, CariGrupForm, StokForm, KasaHareketForm,
    ParaBirimiForm, KasaForm, BankaForm, PosForm, CariHareketForm
)

# Login view
def login_view(request):
    if request.user.is_authenticated:
        return redirect('anasayfa')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('anasayfa')
        else:
            messages.error(request, 'Kullanıcı adı veya şifre hatalı!')
    
    return render(request, 'login.html')

# Logout view
def logout_view(request):
    logout(request)
    return redirect('login')

# Ana sayfa (login sonrası)
@login_required
def anasayfa(request):
    context = {
        'cari_sayisi': CariKart.objects.count(),
        'kasa_sayisi': Kasa.objects.count(),
        'stok_sayisi': StokKart.objects.count(),
        'fatura_sayisi': Fatura.objects.count(),
        'toplam_borc': CariKart.objects.filter(bakiye__lt=0).count(),
        'toplam_alacak': CariKart.objects.filter(bakiye__gt=0).count(),
    }
    return render(request, 'anasayfa.html', context)

# AJAX için ilçe listesi
@login_required
def get_ilceler(request, il_id):
    ilceler = Ilce.objects.filter(il_id=il_id).order_by('ad')
    ilce_list = [{'id': ilce.id, 'ad': ilce.ad} for ilce in ilceler]
    return JsonResponse({'ilceler': ilce_list})

# Cari Grup işlemleri
@login_required
def cari_grup_list(request):
    gruplar = CariGrup.objects.filter(silindi=False).order_by('kod')
    
    if request.method == 'POST':
        form = CariGrupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cari grup eklendi!')
            return redirect('cari_grup_list')
    else:
        form = CariGrupForm()
    
    return render(request, 'cari_grup_list.html', {
        'gruplar': gruplar,
        'form': form
    })

@login_required
def cari_grup_duzenle(request, pk):
    grup = get_object_or_404(CariGrup, pk=pk)
    if request.method == 'POST':
        form = CariGrupForm(request.POST, instance=grup)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cari grup güncellendi!')
            return redirect('cari_grup_list')
    else:
        form = CariGrupForm(instance=grup)
    return render(request, 'cari_grup_form.html', {'form': form, 'title': 'Cari Grup Düzenle'})

@login_required
def cari_grup_sil(request, pk):
    grup = get_object_or_404(CariGrup, pk=pk)
    if request.method == 'POST':
        grup.soft_delete(request.user)  
        messages.success(request, 'Cari grup silindi!')
        return redirect('cari_grup_list')
    return render(request, 'confirm_delete.html', {
        'object': grup,
        'title': 'Cari Grup Sil'
    })

# Cari işlemler
@login_required
def cari_list(request):
    cariler = CariKart.objects.filter(silindi=False).select_related('grup', 'il', 'ilce')
    gruplar = CariGrup.objects.filter(silindi=False).order_by('ad')
    iller = Il.objects.all().order_by('ad')
    
    # Filtreleme parametreleri
    filters = {}
    
    # Metin arama (ünvan, yetkili adı)
    arama = request.GET.get('arama', '').strip()
    if arama:
        cariler = cariler.filter(
            Q(unvan__icontains=arama) |
            Q(kod__icontains=arama) |
            Q(yetkili_adi__icontains=arama) |
            Q(vergi_no__icontains=arama) |
            Q(tc_kimlik__icontains=arama)
        )
        filters['arama'] = arama
    
    # Grup filtresi
    grup_id = request.GET.get('grup')
    if grup_id:
        cariler = cariler.filter(grup_id=grup_id)
        filters['grup'] = grup_id
    
    # İl filtresi
    il_id = request.GET.get('il')
    if il_id:
        cariler = cariler.filter(il_id=il_id)
        filters['il'] = il_id
        # İlçeleri yükle
        filters['ilceler'] = Ilce.objects.filter(il_id=il_id).order_by('ad')
    
    # İlçe filtresi
    ilce_id = request.GET.get('ilce')
    if ilce_id:
        cariler = cariler.filter(ilce_id=ilce_id)
        filters['ilce'] = ilce_id
    
    # Bakiye aralığı
    bakiye_min = request.GET.get('bakiye_min')
    bakiye_max = request.GET.get('bakiye_max')
    
    if bakiye_min:
        try:
            cariler = cariler.filter(bakiye__gte=Decimal(bakiye_min))
            filters['bakiye_min'] = bakiye_min
        except:
            pass
    
    if bakiye_max:
        try:
            cariler = cariler.filter(bakiye__lte=Decimal(bakiye_max))
            filters['bakiye_max'] = bakiye_max
        except:
            pass
    
    # Durum filtresi (aktif/pasif) - VARSAYILAN AKTİF
    if 'durum' not in request.GET:
        durum = 'aktif'
    else:
        durum = request.GET.get('durum')

    if durum == 'aktif':
        cariler = cariler.filter(aktif=True)
        filters['durum'] = 'aktif'
    elif durum == 'pasif':
        cariler = cariler.filter(aktif=False)
        filters['durum'] = 'pasif'
    else:  # durum == '' (Tümü)
        filters['durum'] = ''
    
    # Firma tipi filtresi
    firma_tipi = request.GET.get('firma_tipi')
    if firma_tipi:
        cariler = cariler.filter(firma_tipi=firma_tipi)
        filters['firma_tipi'] = firma_tipi
    
    # Borç/Alacak durumu
    bakiye_durum = request.GET.get('bakiye_durum')
    if bakiye_durum == 'borclu':
        cariler = cariler.filter(bakiye__lt=0)
        filters['bakiye_durum'] = 'borclu'
    elif bakiye_durum == 'alacakli':
        cariler = cariler.filter(bakiye__gt=0)
        filters['bakiye_durum'] = 'alacakli'
    
    # Sıralama
    siralama = request.GET.get('siralama', 'kod')
    if siralama == 'unvan':
        cariler = cariler.order_by('unvan')
    elif siralama == 'bakiye_artan':
        cariler = cariler.order_by('bakiye')
    elif siralama == 'bakiye_azalan':
        cariler = cariler.order_by('-bakiye')
    else:
        cariler = cariler.order_by('kod')
    
    filters['siralama'] = siralama
    
    # Toplam bakiye hesaplama
    toplam_borc = cariler.filter(bakiye__lt=0).aggregate(toplam=models.Sum('bakiye'))['toplam'] or 0
    toplam_alacak = cariler.filter(bakiye__gt=0).aggregate(toplam=models.Sum('bakiye'))['toplam'] or 0
    
    context = {
        'cariler': cariler,
        'gruplar': gruplar,
        'iller': iller,
        'filters': filters,
        'toplam_borc': abs(toplam_borc),
        'toplam_alacak': toplam_alacak,
        'bakiye_net': toplam_alacak + toplam_borc,
    }
    
    return render(request, 'cari_list.html', context)

@login_required
def cari_ekle(request):
    if request.method == 'POST':
        form = CariForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cari kart başarıyla eklendi!')
            return redirect('cari_list')
    else:
        form = CariForm()
    return render(request, 'cari_form.html', {'form': form, 'title': 'Cari Ekle'})

@login_required
def cari_duzenle(request, pk):
    cari = get_object_or_404(CariKart, pk=pk)
    if request.method == 'POST':
        form = CariForm(request.POST, instance=cari)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cari kart güncellendi!')
            return redirect('cari_list')
    else:
        form = CariForm(instance=cari)
    return render(request, 'cari_form.html', {'form': form, 'title': 'Cari Düzenle'})

# Stok işlemler
@login_required
def stok_list(request):
    stoklar = StokKart.objects.all()
    return render(request, 'stok_list.html', {'stoklar': stoklar})

@login_required
def stok_ekle(request):
    if request.method == 'POST':
        form = StokForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stok kartı eklendi!')
            return redirect('stok_list')
    else:
        form = StokForm()
    return render(request, 'stok_form.html', {'form': form})

# Kasa işlemler
@login_required
def kasa_list(request):
    kasalar = Kasa.objects.all()
    hareketler = KasaHareket.objects.select_related('kasa', 'cari').order_by('-tarih')[:20]
    return render(request, 'kasa_list.html', {
        'kasalar': kasalar,
        'hareketler': hareketler
    })

@login_required
def kasa_hareket(request):
    if request.method == 'POST':
        form = KasaHareketForm(request.POST)
        if form.is_valid():
            hareket = form.save(commit=False)
            hareket.olusturan = request.user
            hareket.save()
            
            # Kasa bakiyesini güncelle
            kasa = hareket.kasa
            if hareket.tip == 'giris':
                kasa.bakiye += hareket.tutar
            else:
                kasa.bakiye -= hareket.tutar
            kasa.save()
            
            messages.success(request, 'Kasa hareketi eklendi!')
            return redirect('kasa_list')
    else:
        form = KasaHareketForm()
    return render(request, 'kasa_hareket_form.html', {'form': form})

# Fatura işlemler
@login_required
def fatura_list(request):
    faturalar = Fatura.objects.select_related('cari').all()
    return render(request, 'fatura_list.html', {'faturalar': faturalar})

@login_required
def fatura_ekle(request):
    # Bu kısmı daha sonra detaylandıracağız
    return render(request, 'fatura_form.html')

@login_required
def cari_sil(request, pk):
    cari = get_object_or_404(CariKart, pk=pk)
    if request.method == 'POST':
        cari.soft_delete(request.user)
        messages.success(request, 'Cari kart silindi!')
        return redirect('cari_list')
    return render(request, 'confirm_delete.html', {
        'object': cari,
        'title': 'Cari Kart Sil'
    })

@login_required
def cari_detay(request, pk):
    cari = get_object_or_404(CariKart, pk=pk)
    return render(request, 'cari_detay.html', {'cari': cari})

# Silinen kayıtlar view'ı (sadece superuser)
@login_required
def silinen_kayitlar(request):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    # Tüm silinen kayıtları getir
    silinen_cariler = CariKart.objects.filter(silindi=True)
    silinen_gruplar = CariGrup.objects.filter(silindi=True)
    silinen_stoklar = StokKart.objects.filter(silindi=True)
    
    context = {
        'silinen_cariler': silinen_cariler,
        'silinen_gruplar': silinen_gruplar,
        'silinen_stoklar': silinen_stoklar,
    }
    
    return render(request, 'silinen_kayitlar.html', context)

@login_required
def kayit_geri_yukle(request, model_name, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Bu işlem için yetkiniz yok!')
        return redirect('anasayfa')
    
    # Model'i bul
    if model_name == 'cari':
        obj = get_object_or_404(CariKart, pk=pk)
    elif model_name == 'grup':
        obj = get_object_or_404(CariGrup, pk=pk)
    elif model_name == 'stok':
        obj = get_object_or_404(StokKart, pk=pk)
    else:
        messages.error(request, 'Geçersiz model!')
        return redirect('silinen_kayitlar')
    
    if request.method == 'POST':
        obj.restore()
        messages.success(request, 'Kayıt geri yüklendi!')
        return redirect('silinen_kayitlar')
    
    return render(request, 'confirm_restore.html', {
        'object': obj,
        'model_name': model_name
    })

@login_required
def kayit_kalici_sil(request, model_name, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Bu işlem için yetkiniz yok!')
        return redirect('anasayfa')
    
    # Model'i bul
    if model_name == 'cari':
        obj = get_object_or_404(CariKart, pk=pk)
    elif model_name == 'grup':
        obj = get_object_or_404(CariGrup, pk=pk)
    elif model_name == 'stok':
        obj = get_object_or_404(StokKart, pk=pk)
    else:
        messages.error(request, 'Geçersiz model!')
        return redirect('silinen_kayitlar')
    
    if request.method == 'POST':
        obj.delete()  # Kalıcı silme
        messages.success(request, 'Kayıt kalıcı olarak silindi!')
        return redirect('silinen_kayitlar')
    
    return render(request, 'confirm_permanent_delete.html', {
        'object': obj,
        'model_name': model_name
    })


@login_required
def tumunu_kalici_sil(request, kategori):
    if not request.user.is_superuser:
        messages.error(request, 'Bu işlem için yetkiniz yok!')
        return redirect('anasayfa')
    
    if request.method == 'POST':
        if kategori == 'cari':
            silinecekler = CariKart.objects.filter(silindi=True)
            sayi = silinecekler.count()
            silinecekler.delete()
            messages.success(request, f'{sayi} adet cari kaydı kalıcı olarak silindi!')
        elif kategori == 'grup':
            silinecekler = CariGrup.objects.filter(silindi=True)
            sayi = silinecekler.count()
            silinecekler.delete()
            messages.success(request, f'{sayi} adet cari grubu kalıcı olarak silindi!')
        elif kategori == 'stok':
            silinecekler = StokKart.objects.filter(silindi=True)
            sayi = silinecekler.count()
            silinecekler.delete()
            messages.success(request, f'{sayi} adet stok kaydı kalıcı olarak silindi!')
        else:
            messages.error(request, 'Geçersiz kategori!')
    
    return redirect('silinen_kayitlar')

@login_required
def yetkili_menu(request):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    context = {
        'para_birimleri': ParaBirimi.objects.filter(silindi=False).count(),
        'kasalar': Kasa.objects.filter(silindi=False).count(),
        'bankalar': Banka.objects.filter(silindi=False).count(),
        'poslar': Pos.objects.filter(silindi=False).count(),
    }
    return render(request, 'yetkili/menu.html', context)


@login_required
def para_birimi_list(request):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    para_birimleri = ParaBirimi.objects.filter(silindi=False)
    return render(request, 'yetkili/para_birimi_list.html', {'para_birimleri': para_birimleri})


@login_required
def kasa_list(request):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    kasalar = Kasa.objects.filter(silindi=False).select_related('para_birimi')
    return render(request, 'yetkili/kasa_list.html', {'kasalar': kasalar})


@login_required
def banka_list(request):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    bankalar = Banka.objects.filter(silindi=False).select_related('para_birimi')
    return render(request, 'yetkili/banka_list.html', {'bankalar': bankalar})


@login_required
def pos_list(request):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    poslar = Pos.objects.filter(silindi=False).select_related('banka')
    return render(request, 'yetkili/pos_list.html', {'poslar': poslar})


# muhasebe/views.py - Eksik view fonksiyonlarını ekleyin

# Para Birimi işlemleri
@login_required
def para_birimi_ekle(request):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    if request.method == 'POST':
        form = ParaBirimiForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Para birimi eklendi!')
            return redirect('para_birimi_list')
    else:
        form = ParaBirimiForm()
    
    return render(request, 'yetkili/para_birimi_form.html', {'form': form, 'title': 'Para Birimi Ekle'})

@login_required
def para_birimi_duzenle(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    para_birimi = get_object_or_404(ParaBirimi, pk=pk)
    if request.method == 'POST':
        form = ParaBirimiForm(request.POST, instance=para_birimi)
        if form.is_valid():
            form.save()
            messages.success(request, 'Para birimi güncellendi!')
            return redirect('para_birimi_list')
    else:
        form = ParaBirimiForm(instance=para_birimi)
    
    return render(request, 'yetkili/para_birimi_form.html', {'form': form, 'title': 'Para Birimi Düzenle'})

# Kasa işlemleri
@login_required
def kasa_ekle(request):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    if request.method == 'POST':
        form = KasaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kasa eklendi!')
            return redirect('kasa_list')
    else:
        form = KasaForm()
    
    return render(request, 'yetkili/kasa_form.html', {'form': form, 'title': 'Kasa Ekle'})

@login_required
def kasa_duzenle(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    kasa = get_object_or_404(Kasa, pk=pk)
    if request.method == 'POST':
        form = KasaForm(request.POST, instance=kasa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kasa güncellendi!')
            return redirect('kasa_list')
    else:
        form = KasaForm(instance=kasa)
    
    return render(request, 'yetkili/kasa_form.html', {'form': form, 'title': 'Kasa Düzenle'})

# Banka işlemleri
@login_required
def banka_ekle(request):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    if request.method == 'POST':
        form = BankaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Banka eklendi!')
            return redirect('banka_list')
    else:
        form = BankaForm()
    
    return render(request, 'yetkili/banka_form.html', {'form': form, 'title': 'Banka Ekle'})

@login_required
def banka_duzenle(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    banka = get_object_or_404(Banka, pk=pk)
    if request.method == 'POST':
        form = BankaForm(request.POST, instance=banka)
        if form.is_valid():
            form.save()
            messages.success(request, 'Banka güncellendi!')
            return redirect('banka_list')
    else:
        form = BankaForm(instance=banka)
    
    return render(request, 'yetkili/banka_form.html', {'form': form, 'title': 'Banka Düzenle'})

# POS işlemleri
@login_required
def pos_ekle(request):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    if request.method == 'POST':
        form = PosForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'POS eklendi!')
            return redirect('pos_list')
    else:
        form = PosForm()
    
    return render(request, 'yetkili/pos_form.html', {'form': form, 'title': 'POS Ekle'})

@login_required
def pos_duzenle(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    pos = get_object_or_404(Pos, pk=pk)
    if request.method == 'POST':
        form = PosForm(request.POST, instance=pos)
        if form.is_valid():
            form.save()
            messages.success(request, 'POS güncellendi!')
            return redirect('pos_list')
    else:
        form = PosForm(instance=pos)
    
    return render(request, 'yetkili/pos_form.html', {'form': form, 'title': 'POS Düzenle'})

# Cari Hareket işlemleri
@login_required
def cari_hareket_list(request):
    hareketler = CariHareket.objects.filter(silindi=False).select_related('cari', 'para_birimi', 'kasa', 'banka', 'pos')
    return render(request, 'cari_hareket/list.html', {'hareketler': hareketler})

@login_required
def cari_hareket_ekle(request):
    if request.method == 'POST':
        form = CariHareketForm(request.POST)
        if form.is_valid():
            hareket = form.save(commit=False)
            hareket.olusturan = request.user
            hareket.tutar = form.cleaned_data['tutar']
            hareket.hareket_yonu = form.cleaned_data['hareket_yonu']
            hareket.save()
            messages.success(request, 'Cari hareket eklendi!')
            return redirect('cari_hareket_list')
    else:
        form = CariHareketForm()
    
    return render(request, 'cari_hareket/form.html', {'form': form, 'title': 'Cari Hareket Ekle'})

@login_required
def cari_hareketler(request, cari_id):
    cari = get_object_or_404(CariKart, pk=cari_id)
    hareketler = cari.hareketler.filter(silindi=False).order_by('-tarih')
    return render(request, 'cari_hareket/cari_hareketler.html', {
        'cari': cari,
        'hareketler': hareketler
    })

# AJAX view'ları
@login_required
def cari_ara(request):
    q = request.GET.get('q', '')
    cariler = CariKart.objects.filter(
        silindi=False,
        aktif=True,
        unvan__icontains=q
    )[:20]
    
    data = []
    for cari in cariler:
        data.append({
            'id': cari.id,
            'text': f"{cari.kod} - {cari.unvan}",
            'bakiye': str(cari.bakiye)
        })
    
    return JsonResponse({'results': data})

@login_required
def kasa_banka_getir(request):
    para_birimi_id = request.GET.get('para_birimi_id')
    islem_tipi = request.GET.get('islem_tipi')
    
    data = {'items': []}
    
    if para_birimi_id and islem_tipi:
        if islem_tipi == 'nakit':
            kasalar = Kasa.objects.filter(
                silindi=False,
                aktif=True,
                para_birimi_id=para_birimi_id
            )
            for kasa in kasalar:
                data['items'].append({
                    'id': kasa.id,
                    'text': f"{kasa.kod} - {kasa.ad}"
                })
        elif islem_tipi == 'banka':
            bankalar = Banka.objects.filter(
                silindi=False,
                aktif=True,
                para_birimi_id=para_birimi_id
            )
            for banka in bankalar:
                data['items'].append({
                    'id': banka.id,
                    'text': f"{banka.kod} - {banka.ad}"
                })
        elif islem_tipi == 'pos':
            poslar = Pos.objects.filter(
                silindi=False,
                aktif=True,
                banka__para_birimi_id=para_birimi_id
            )
            for pos in poslar:
                data['items'].append({
                    'id': pos.id,
                    'text': f"{pos.kod} - {pos.ad}"
                })
    
    return JsonResponse(data)