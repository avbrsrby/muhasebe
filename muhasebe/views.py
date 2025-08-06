from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from django.utils import timezone
from django.db.models import Sum, Q, Count, F, Value
from django.db.models.functions import Coalesce, Abs
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
from .models import Fatura, FaturaKalem  # Fatura modellerini import'a ekle
from .forms import FaturaForm 

from .models import (
    CariKart, CariGrup, Kasa, Banka, StokKart, Fatura, KasaHareket, 
    Il, Ilce, ParaBirimi, Pos, CariHareket,
    StokGrupFiyat, StokSecenek, StokSecenekDeger,
    GenelStokSecenek, GenelStokSecenekDeger, StokGrup
)



# Form import'ları  
from .forms import (
    CariForm, CariGrupForm, StokForm, KasaHareketForm,
    ParaBirimiForm, KasaForm, BankaForm, PosForm, CariHareketForm, CariVirmanForm, StokGrupForm
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
        'cari_sayisi': CariKart.objects.filter(silindi=False).count(),
        'kasa_sayisi': Kasa.objects.filter(silindi=False).count(),
        'stok_sayisi': StokKart.objects.filter(silindi=False).count(),
        'fatura_sayisi': Fatura.objects.filter(silindi=False).count(),
    }
    
    # Bakiye hesaplamaları
    from django.db.models import Sum, Q, F, DecimalField
    from decimal import Decimal
    
    try:
        tl = ParaBirimi.objects.get(kod='TL')
        
        # Tüm carilerin TL bakiyelerini hesapla
        cariler_bakiye = CariHareket.objects.filter(
            silindi=False,
            para_birimi=tl
        ).values('cari').annotate(
            toplam_giris=Sum('tutar', filter=Q(hareket_yonu='giris'), default=Decimal('0')),
            toplam_cikis=Sum('tutar', filter=Q(hareket_yonu='cikis'), default=Decimal('0'))
        ).annotate(
            bakiye=F('toplam_giris') - F('toplam_cikis')
        )
        
        # Borçlu ve alacaklı cari sayıları ve toplamları
        toplam_borc = Decimal('0')
        toplam_alacak = Decimal('0')
        toplam_borc_sayisi = 0
        toplam_alacak_sayisi = 0
        
        for cari in cariler_bakiye:
            bakiye = cari['bakiye'] or Decimal('0')
            if bakiye < 0:
                toplam_borc += abs(bakiye)
                toplam_borc_sayisi += 1
            elif bakiye > 0:
                toplam_alacak += bakiye
                toplam_alacak_sayisi += 1
        
        context['toplam_borc'] = toplam_borc
        context['toplam_alacak'] = toplam_alacak
        context['net_bakiye'] = toplam_alacak - toplam_borc
        context['toplam_borc_sayisi'] = toplam_borc_sayisi
        context['toplam_alacak_sayisi'] = toplam_alacak_sayisi
        
    except ParaBirimi.DoesNotExist:
        context['toplam_borc'] = Decimal('0')
        context['toplam_alacak'] = Decimal('0')
        context['net_bakiye'] = Decimal('0')
        context['toplam_borc_sayisi'] = 0
        context['toplam_alacak_sayisi'] = 0
    
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
    arama = request.GET.get('cari_ara', '').strip()
    if arama:
        cariler = cariler.filter(
            Q(unvan__icontains=arama) |
            Q(kod__icontains=arama) |
            Q(yetkili_adi__icontains=arama) |
            Q(vergi_no__icontains=arama) |
            Q(tc_kimlik__icontains=arama) |
            Q(telefon__icontains=arama) |         
            Q(email__icontains=arama) |            
            Q(adres__icontains=arama)
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
    

    
    # TL para birimi için bakiye hesapla
    try:
        tl = ParaBirimi.objects.get(kod='TL')
        
        # Her cari için bakiye hesapla
        cariler = cariler.annotate(
            toplam_giris=Sum(
                'hareketler__tutar',
                filter=Q(
                    hareketler__hareket_yonu='giris',
                    hareketler__para_birimi=tl,
                    hareketler__silindi=False
                ),
                default=Decimal('0')
            ),
            toplam_cikis=Sum(
                'hareketler__tutar',
                filter=Q(
                    hareketler__hareket_yonu='cikis',
                    hareketler__para_birimi=tl,
                    hareketler__silindi=False
                ),
                default=Decimal('0')
            )
        ).annotate(
            bakiye_hesaplanan=F('toplam_giris') - F('toplam_cikis')
        )
        
        # Bakiye aralığı filtreleri
        bakiye_min = request.GET.get('bakiye_min')
        bakiye_max = request.GET.get('bakiye_max')
        
        if bakiye_min:
            try:
                cariler = cariler.filter(bakiye_hesaplanan__gte=Decimal(bakiye_min))
                filters['bakiye_min'] = bakiye_min
            except:
                pass
        
        if bakiye_max:
            try:
                cariler = cariler.filter(bakiye_hesaplanan__lte=Decimal(bakiye_max))
                filters['bakiye_max'] = bakiye_max
            except:
                pass
        
        # Borç/Alacak durumu
        bakiye_durum = request.GET.get('bakiye_durum')
        if bakiye_durum == 'borclu':
            cariler = cariler.filter(bakiye_hesaplanan__lt=0)
            filters['bakiye_durum'] = 'borclu'
        elif bakiye_durum == 'alacakli':
            cariler = cariler.filter(bakiye_hesaplanan__gt=0)
            filters['bakiye_durum'] = 'alacakli'
        
        # Sıralama
        # Sıralama kısmını değiştirin:
        # Sıralama
        siralama = request.GET.get('siralama', 'bakiye_azalan')  # Varsayılan değer değişti
        if siralama == 'unvan':
            cariler = cariler.order_by('unvan')
        elif siralama == 'bakiye_artan':
            # Mutlak değere göre artan sıralama
            cariler = cariler.annotate(
                bakiye_mutlak=Abs('bakiye_hesaplanan')
            ).order_by('bakiye_mutlak')
        elif siralama == 'bakiye_azalan':
            # Mutlak değere göre azalan sıralama
            cariler = cariler.annotate(
                bakiye_mutlak=Abs('bakiye_hesaplanan')
            ).order_by('-bakiye_mutlak')
        else:
            # Varsayılan olarak bakiye azalan
            cariler = cariler.annotate(
                bakiye_mutlak=Abs('bakiye_hesaplanan')
            ).order_by('-bakiye_mutlak')

        filters['siralama'] = siralama
        
        # Toplam bakiye hesaplama
        toplam_borc = cariler.filter(bakiye_hesaplanan__lt=0).aggregate(
            toplam=Sum('bakiye_hesaplanan')
        )['toplam'] or Decimal('0')
        
        toplam_alacak = cariler.filter(bakiye_hesaplanan__gt=0).aggregate(
            toplam=Sum('bakiye_hesaplanan')
        )['toplam'] or Decimal('0')
        
    except ParaBirimi.DoesNotExist:
        # TL yoksa bakiye hesaplama yapma
        toplam_borc = Decimal('0')
        toplam_alacak = Decimal('0')
        
        # Sıralama
        siralama = request.GET.get('siralama', 'kod')
        if siralama == 'unvan':
            cariler = cariler.order_by('unvan')
        else:
            cariler = cariler.order_by('kod')
        filters['siralama'] = siralama
    
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
    stoklar = StokKart.objects.filter(silindi=False).select_related('para_birimi', 'grup')
    
    # Filtreleme parametreleri
    filters = {}
    
    # Metin arama (ad, kod, barkod)
    arama = request.GET.get('arama', '').strip()
    if arama:
        stoklar = stoklar.filter(
            Q(kod__icontains=arama) | 
            Q(ad__icontains=arama) | 
            Q(barkod__icontains=arama)
        )
        filters['arama'] = arama
    
    # Stok grubu filtresi
    grup_id = request.GET.get('grup')
    if grup_id:
        stoklar = stoklar.filter(grup_id=grup_id)
        filters['grup'] = grup_id
    
    # YENİ KOD:
    # Para birimi filtresi
    para_birimi_id = request.GET.get('para_birimi')
    if para_birimi_id:
        stoklar = stoklar.filter(para_birimi_id=para_birimi_id)
        filters['para_birimi'] = para_birimi_id
    
    # Fiyat aralığı filtreleri
    satis_fiyati_min = request.GET.get('satis_fiyati_min')
    satis_fiyati_max = request.GET.get('satis_fiyati_max')
    
    if satis_fiyati_min:
        try:
            stoklar = stoklar.filter(satis_fiyati__gte=Decimal(satis_fiyati_min))
            filters['satis_fiyati_min'] = satis_fiyati_min
        except:
            pass
    
    if satis_fiyati_max:
        try:
            stoklar = stoklar.filter(satis_fiyati__lte=Decimal(satis_fiyati_max))
            filters['satis_fiyati_max'] = satis_fiyati_max
        except:
            pass
    
    # Durum filtresi
    durum = request.GET.get('durum')
    if durum == 'aktif':
        stoklar = stoklar.filter(aktif=True)
        filters['durum'] = 'aktif'
    elif durum == 'pasif':
        stoklar = stoklar.filter(aktif=False)
        filters['durum'] = 'pasif'
    
    # Kritik stok filtresi
    kritik_stok = request.GET.get('kritik_stok')
    if kritik_stok == 'kritik':
        stoklar = stoklar.filter(miktar__lte=F('kritik_stok'))
        filters['kritik_stok'] = 'kritik'
    
    # Sıralama
    siralama = request.GET.get('siralama', 'kod')
    if siralama == 'ad':
        stoklar = stoklar.order_by('ad')
    elif siralama == 'fiyat_artan':
        stoklar = stoklar.order_by('satis_fiyati')
    elif siralama == 'fiyat_azalan':
        stoklar = stoklar.order_by('-satis_fiyati')
    elif siralama == 'stok_artan':
        stoklar = stoklar.order_by('miktar')
    elif siralama == 'stok_azalan':
        stoklar = stoklar.order_by('-miktar')
    else:
        stoklar = stoklar.order_by('kod')
    filters['siralama'] = siralama
    
    # Toplam değer hesapla
    toplam_deger = stoklar.aggregate(
        toplam=Sum(F('miktar') * F('satis_fiyati'))
    )['toplam'] or Decimal('0')
    
    # Kritik stok sayısı
    kritik_stok_sayisi = stoklar.filter(miktar__lte=F('kritik_stok')).count()
    
    context = {
        'stoklar': stoklar,
        'filters': filters,
        'para_birimleri': ParaBirimi.objects.filter(silindi=False, aktif=True),
        'stok_gruplari': StokGrup.objects.filter(silindi=False, aktif=True).order_by('ad'),
        'toplam_deger': toplam_deger,
        'kritik_stok_sayisi': kritik_stok_sayisi,
    }
    
    return render(request, 'stok/list.html', context)


@login_required
def stok_ekle(request):
    if request.method == 'POST':
        form = StokForm(request.POST, user=request.user)  # user parametresi ekle
        if form.is_valid():
            stok = form.save()
            messages.success(request, 'Stok kartı başarıyla eklendi!')
            return redirect('stok_list')
    else:
        form = StokForm(user=request.user)  # user parametresi ekle

    # Cari grupları ekle
    cari_gruplar = CariGrup.objects.filter(silindi=False, aktif=True).order_by('ad')
    
    return render(request, 'stok/form.html', {
        'form': form,
        'title': 'Yeni Stok Ekle',
        'cari_gruplar': cari_gruplar
    })

@login_required
def stok_duzenle(request, pk):
    stok = get_object_or_404(StokKart, pk=pk, silindi=False)
    
    if request.method == 'POST':
        form = StokForm(request.POST, instance=stok, user=request.user)  # user parametresi ekle
        if form.is_valid():
            form.save()
            messages.success(request, 'Stok kartı güncellendi!')
            return redirect('stok_list')
    else:
        form = StokForm(instance=stok, user=request.user)  # user parametresi ekle

    # Cari grupları ekle
    cari_gruplar = CariGrup.objects.filter(silindi=False, aktif=True).order_by('ad')
    
    return render(request, 'stok/form.html', {
        'form': form,
        'title': 'Stok Düzenle',
        'stok': stok,
        'cari_gruplar': cari_gruplar
    })




@login_required
def stok_sil(request, pk):
    stok = get_object_or_404(StokKart, pk=pk)
    if request.method == 'POST':
        stok.soft_delete(request.user)
        messages.success(request, 'Stok kartı silindi!')
        return redirect('stok_list')
    
    return render(request, 'confirm_delete.html', {
        'object': stok,
        'title': 'Stok Kartı Sil'
    })



# Stok Grup işlemleri
@login_required
def stok_grup_list(request):
    gruplar = StokGrup.objects.filter(silindi=False).order_by('kod')
    
    if request.method == 'POST':
        form = StokGrupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stok grubu eklendi!')
            return redirect('stok_grup_list')
    else:
        form = StokGrupForm()
    
    return render(request, 'stok/grup_list.html', {
        'gruplar': gruplar,
        'form': form
    })

@login_required
def stok_grup_duzenle(request, pk):
    grup = get_object_or_404(StokGrup, pk=pk)
    if request.method == 'POST':
        form = StokGrupForm(request.POST, instance=grup)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stok grubu güncellendi!')
            return redirect('stok_grup_list')
    else:
        form = StokGrupForm(instance=grup)
    return render(request, 'stok/grup_form.html', {'form': form, 'title': 'Stok Grubu Düzenle'})

@login_required
def stok_grup_sil(request, pk):
    grup = get_object_or_404(StokGrup, pk=pk)
    if request.method == 'POST':
        grup.soft_delete(request.user)
        messages.success(request, 'Stok grubu silindi!')
        return redirect('stok_grup_list')
    return render(request, 'confirm_delete.html', {
        'object': grup,
        'title': 'Stok Grubu Sil'
    })


# AJAX view'lar
@login_required
def stok_grup_fiyat_ekle(request, stok_id):
    if request.method == 'POST':
        stok = get_object_or_404(StokKart, pk=stok_id, silindi=False)
        cari_grup_id = request.POST.get('cari_grup_id')
        satis_fiyati = request.POST.get('satis_fiyati')
        
        # Aynı grup için fiyat var mı kontrol et
        if StokGrupFiyat.objects.filter(stok=stok, cari_grup_id=cari_grup_id, silindi=False).exists():
            return JsonResponse({'success': False, 'error': 'Bu grup için fiyat zaten tanımlı!'})
        
        try:
            grup_fiyat = StokGrupFiyat.objects.create(
                stok=stok,
                cari_grup_id=cari_grup_id,
                satis_fiyati=satis_fiyati
            )
            
            return JsonResponse({
                'success': True,
                'id': grup_fiyat.id,
                'grup_adi': grup_fiyat.cari_grup.ad,
                'fiyat': str(grup_fiyat.satis_fiyati)
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Geçersiz istek'})


@login_required
def stok_grup_fiyat_sil(request, pk):
    if request.method == 'POST':
        grup_fiyat = get_object_or_404(StokGrupFiyat, pk=pk)
        grup_fiyat.soft_delete(request.user)
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})


@login_required
def stok_secenek_ekle(request, stok_id):
    if request.method == 'POST':
        stok = get_object_or_404(StokKart, pk=stok_id, silindi=False)
        baslik = request.POST.get('baslik')
        
        # Son sıra numarasını bul
        son_sira = stok.secenekler.filter(silindi=False).aggregate(
            max_sira=models.Max('sira')
        )['max_sira'] or 0
        
        secenek = StokSecenek.objects.create(
            stok=stok,
            baslik=baslik,
            sira=son_sira + 1
        )
        
        return JsonResponse({
            'success': True,
            'id': secenek.id,
            'baslik': secenek.baslik
        })
    
    return JsonResponse({'success': False})


@login_required
def stok_secenek_deger_ekle(request, secenek_id):
    if request.method == 'POST':
        secenek = get_object_or_404(StokSecenek, pk=secenek_id, silindi=False)
        
        deger = request.POST.get('deger')
        fiyat_tipi = request.POST.get('fiyat_tipi')
        fiyat_degeri = request.POST.get('fiyat_degeri')
        varsayilan = request.POST.get('varsayilan') == 'true'  # YENİ
        
        # Son sıra numarasını bul
        son_sira = secenek.degerler.filter(silindi=False).aggregate(
            max_sira=models.Max('sira')
        )['max_sira'] or 0
        
        secenek_deger = StokSecenekDeger.objects.create(
            secenek=secenek,
            deger=deger,
            fiyat_tipi=fiyat_tipi,
            fiyat_degeri=fiyat_degeri,
            sira=son_sira + 1,
            varsayilan=varsayilan  # YENİ
        )
        
        return JsonResponse({
            'success': True,
            'id': secenek_deger.id,
            'deger': secenek_deger.deger,
            'fiyat_gosterim': f"{'%' if fiyat_tipi == 'yuzde' else ''}{fiyat_degeri}",
            'varsayilan': secenek_deger.varsayilan  # YENİ
        })
    
    return JsonResponse({'success': False})



@login_required
def stok_secenek_deger_sil(request, pk):
    if request.method == 'POST':
        deger = get_object_or_404(StokSecenekDeger, pk=pk)
        deger.soft_delete(request.user)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@login_required
def stok_secenek_deger_duzenle(request, pk):
    if request.method == 'POST':
        deger = get_object_or_404(StokSecenekDeger, pk=pk)
        deger.deger = request.POST.get('deger')
        deger.fiyat_tipi = request.POST.get('fiyat_tipi')
        deger.fiyat_degeri = request.POST.get('fiyat_degeri')
        deger.varsayilan = request.POST.get('varsayilan') == 'true'
        deger.save()
        
        return JsonResponse({
            'success': True,
            'varsayilan': deger.varsayilan
        })
    return JsonResponse({'success': False})

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
    faturalar = Fatura.objects.filter(silindi=False).select_related('cari', 'olusturan')
    
    # Filtreleme
    tip = request.GET.get('tip')
    if tip:
        faturalar = faturalar.filter(tip=tip)
    
    tarih_bas = request.GET.get('tarih_bas')
    if tarih_bas:
        faturalar = faturalar.filter(tarih__date__gte=tarih_bas)
    
    tarih_son = request.GET.get('tarih_son')
    if tarih_son:
        faturalar = faturalar.filter(tarih__date__lte=tarih_son)
    
    cari_ara = request.GET.get('cari_ara')
    if cari_ara:
        faturalar = faturalar.filter(
            Q(cari__unvan__icontains=cari_ara) | 
            Q(cari__kod__icontains=cari_ara)
        )
    
    # Toplam tutarlar
    toplam_satis = faturalar.filter(tip='satis').aggregate(
        toplam=Sum('genel_toplam')
    )['toplam'] or Decimal('0')
    
    toplam_alis = faturalar.filter(tip='alis').aggregate(
        toplam=Sum('genel_toplam')
    )['toplam'] or Decimal('0')
    
    context = {
        'faturalar': faturalar.order_by('-tarih', '-id'),
        'toplam_satis': toplam_satis,
        'toplam_alis': toplam_alis,
    }
    
    return render(request, 'fatura/list.html', context)

@login_required
def fatura_ekle(request):
    if request.method == 'POST':
        form = FaturaForm(request.POST)
        if form.is_valid():
            fatura = form.save(commit=False)
            fatura.olusturan = request.user
            fatura.save()
            
            # Kalemler JSON olarak gelecek
            kalemler_json = request.POST.get('kalemler')
            if kalemler_json:
                import json
                kalemler = json.loads(kalemler_json)
                
                ara_toplam = Decimal('0')
                toplam_kdv = Decimal('0')
                
                for kalem_data in kalemler:
                    stok = StokKart.objects.get(pk=kalem_data['stok_id'])
                    
                    # Fiyat hesaplama
                    birim_fiyat = Decimal(str(kalem_data['birim_fiyat']))
                    secenek_fiyat_farki = Decimal(str(kalem_data.get('secenek_fiyat_farki', 0)))
                    
                    # İndirim hesaplama
                    indirim_orani = Decimal('0')
                    indirim_aciklama = ''
                    
                    # Cari grup indirimi kontrol et
                    if fatura.cari.grup:
                        grup_fiyat = StokGrupFiyat.objects.filter(
                            stok=stok,
                            cari_grup=fatura.cari.grup,
                            silindi=False
                        ).first()
                        
                        if grup_fiyat:
                            # Grup özel fiyatı var
                            eski_fiyat = birim_fiyat
                            birim_fiyat = grup_fiyat.satis_fiyati
                            if eski_fiyat > 0:
                                indirim_orani = ((eski_fiyat - birim_fiyat) / eski_fiyat) * 100
                                indirim_aciklama = f"{fatura.cari.grup.ad} grubuna özel fiyat"
                    
                    kalem = FaturaKalem.objects.create(
                        fatura=fatura,
                        stok=stok,
                        miktar=Decimal(str(kalem_data['miktar'])),
                        birim_fiyat=birim_fiyat,
                        kdv_orani=kalem_data.get('kdv_orani', stok.kdv_orani),
                        kdv_durumu=kalem_data.get('kdv_durumu', 'dahil'),
                        indirim_orani=indirim_orani,
                        indirim_aciklama=indirim_aciklama,
                        secenekler=kalem_data.get('secenekler', {}),
                        secenek_fiyat_farki=secenek_fiyat_farki
                    )
                    
                    
                
                # Fatura toplamlarını güncelle
                # Kalemleri kaydettikten sonra toplamları yeniden hesapla
                ara_toplam = Decimal('0')
                toplam_kdv = Decimal('0')

                for kalem in fatura.kalemler.all():
                        # tutar alanı zaten net tutar (KDV hariç)
                    ara_toplam += kalem.tutar
                    toplam_kdv += kalem.kdv_tutari

                # Fatura toplamlarını güncelle
                fatura.ara_toplam = ara_toplam

                # Fatura iskontosu
                if fatura.iskonto_tipi == 'yuzde' and fatura.iskonto_degeri > 0:
                    fatura.iskonto_tutari = ara_toplam * fatura.iskonto_degeri / Decimal('100')
                elif fatura.iskonto_tipi == 'tutar':
                    fatura.iskonto_tutari = fatura.iskonto_degeri
                else:
                    fatura.iskonto_tutari = Decimal('0')

                # İskontolu ara toplam
                iskontolu_ara_toplam = ara_toplam - fatura.iskonto_tutari

                # Genel toplam
                fatura.kdv_tutari = toplam_kdv
                fatura.genel_toplam = iskontolu_ara_toplam + toplam_kdv
                fatura.save()
                
                # Stok güncelleme (satış ise düş, alış ise ekle)
                for kalem in fatura.kalemler.all():
                    if fatura.tip == 'satis':
                        kalem.stok.miktar -= kalem.miktar
                    else:  # alış
                        kalem.stok.miktar += kalem.miktar
                    kalem.stok.save()
            
            messages.success(request, 'Fatura başarıyla oluşturuldu!')
            return redirect('fatura_duzenle', pk=fatura.pk)
    else:
        form = FaturaForm()
    
    return render(request, 'fatura/form.html', {
        'form': form,
        'title': 'Yeni Fatura'
    })


@login_required
def fatura_duzenle(request, pk):
    fatura = get_object_or_404(Fatura, pk=pk, silindi=False)
    
    if request.method == 'POST':
        form = FaturaForm(request.POST, instance=fatura)
        if form.is_valid():
            # Önce eski stok durumlarını geri al
            for kalem in fatura.kalemler.all():
                if fatura.tip == 'satis':
                    kalem.stok.miktar += kalem.miktar
                else:
                    kalem.stok.miktar -= kalem.miktar
                kalem.stok.save()
                kalem.delete()
            
            # Yeni kalemleri kaydet
            fatura = form.save()
            
            kalemler_json = request.POST.get('kalemler')
            if kalemler_json:
                kalemler = json.loads(kalemler_json)
                
                ara_toplam = Decimal('0')
                toplam_kdv = Decimal('0')
                
                for kalem_data in kalemler:
                    stok = StokKart.objects.get(pk=kalem_data['stok_id'])
                    
                    # İndirim hesaplama
                    birim_fiyat = Decimal(str(kalem_data['birim_fiyat']))
                    indirim_orani = Decimal('0')
                    indirim_aciklama = ''
                    
                    # Cari grup indirimi kontrol et
                    if fatura.cari.grup:
                        grup_fiyat = StokGrupFiyat.objects.filter(
                            stok=stok,
                            cari_grup=fatura.cari.grup,
                            silindi=False
                        ).first()
                        
                        if grup_fiyat:
                            eski_fiyat = birim_fiyat
                            birim_fiyat = grup_fiyat.satis_fiyati
                            if eski_fiyat > 0:
                                indirim_orani = ((eski_fiyat - birim_fiyat) / eski_fiyat) * 100
                                indirim_aciklama = f"{fatura.cari.grup.ad} grubuna özel fiyat"
                    
                    kalem = FaturaKalem.objects.create(
                        fatura=fatura,
                        stok=stok,
                        miktar=Decimal(str(kalem_data['miktar'])),
                        birim_fiyat=birim_fiyat,
                        kdv_orani=kalem_data.get('kdv_orani', stok.kdv_orani),
                        kdv_durumu=kalem_data.get('kdv_durumu', 'dahil'),
                        indirim_orani=indirim_orani,
                        indirim_aciklama=indirim_aciklama,
                        secenekler=kalem_data.get('secenekler', {}),
                        secenek_fiyat_farki=Decimal(str(kalem_data.get('secenek_fiyat_farki', 0)))
                    )
                    
                    
                    
                    # Yeni stok durumunu güncelle
                    if fatura.tip == 'satis':
                        kalem.stok.miktar -= kalem.miktar
                    else:
                        kalem.stok.miktar += kalem.miktar
                    kalem.stok.save()
                
                # Fatura toplamlarını güncelle
                fatura.ara_toplam = ara_toplam
                
                # Fatura iskontosu
                if fatura.iskonto_tipi == 'yuzde' and fatura.iskonto_degeri > 0:
                    fatura.iskonto_tutari = ara_toplam * fatura.iskonto_degeri / Decimal('100')
                elif fatura.iskonto_tipi == 'tutar':
                    fatura.iskonto_tutari = fatura.iskonto_degeri
                
                # İskontolu ara toplam
                iskontolu_ara_toplam = ara_toplam - fatura.iskonto_tutari
                
                fatura.kdv_tutari = toplam_kdv
                fatura.genel_toplam = iskontolu_ara_toplam + toplam_kdv
                fatura.save()
            
            messages.success(request, 'Fatura güncellendi!')
            return redirect('fatura_duzenle', pk=fatura.pk)
    else:
        form = FaturaForm(instance=fatura)
    
    return render(request, 'fatura/form.html', {
        'form': form,
        'fatura': fatura,
        'title': f'Fatura Düzenle - {fatura.fatura_no}',
        'kalemler': list(fatura.kalemler.filter(silindi=False).values(
            'id', 'stok__id', 'stok__kod', 'stok__ad', 'miktar', 
            'birim_fiyat', 'kdv_orani', 'kdv_durumu', 'secenekler', 
            'secenek_fiyat_farki', 'indirim_orani', 'indirim_aciklama'
        ))
    })

@login_required
def fatura_sil(request, pk):
    fatura = get_object_or_404(Fatura, pk=pk)
    
    if request.method == 'POST' or request.method == 'GET':  # GET'i de kabul et
        # Stokları geri al
        for kalem in fatura.kalemler.all():
            if fatura.tip == 'satis':
                kalem.stok.miktar += kalem.miktar
            else:
                kalem.stok.miktar -= kalem.miktar
            kalem.stok.save()
        
        # Faturayı soft delete yap
        fatura.soft_delete(request.user)
        messages.success(request, 'Fatura silindi!')
        return redirect('fatura_list')
    
    return redirect('fatura_list')

# AJAX endpoint'leri
@login_required
def get_stok_detay(request, stok_id):
    """Stok detaylarını ve seçeneklerini döndür"""
    stok = get_object_or_404(StokKart, pk=stok_id, silindi=False)
    
    # Seçenekleri hazırla
    secenekler = []
    for secenek in stok.secenekler.filter(silindi=False).order_by('sira'):
        degerler = []
        for deger in secenek.degerler.filter(silindi=False).order_by('sira'):
            degerler.append({
                'id': deger.id,
                'deger': deger.deger,
                'fiyat_tipi': deger.fiyat_tipi,
                'fiyat_degeri': str(deger.fiyat_degeri),
                'varsayilan': deger.varsayilan
            })
        
        secenekler.append({
            'id': secenek.id,
            'baslik': secenek.baslik,
            'degerler': degerler
        })
    
    # Cari grup fiyatı kontrol et
    cari_id = request.GET.get('cari_id')
    ozel_fiyat = None
    indirim_bilgisi = None
    
    if cari_id:
        cari = CariKart.objects.get(pk=cari_id)
        if cari.grup:
            grup_fiyat = StokGrupFiyat.objects.filter(
                stok=stok,
                cari_grup=cari.grup,
                silindi=False
            ).first()
            
            if grup_fiyat:
                ozel_fiyat = str(grup_fiyat.satis_fiyati)
                if stok.satis_fiyati > 0:
                    indirim_orani = ((stok.satis_fiyati - grup_fiyat.satis_fiyati) / stok.satis_fiyati) * 100
                    indirim_bilgisi = {
                        'eski_fiyat': str(stok.satis_fiyati),
                        'yeni_fiyat': ozel_fiyat,
                        'indirim_orani': str(round(indirim_orani, 2)),
                        'aciklama': f"{cari.grup.ad} grubuna özel fiyat"
                    }
    
    data = {
        'id': stok.id,
        'kod': stok.kod,
        'ad': stok.ad,
        'birim': stok.get_birim_display(),
        'miktar': str(stok.miktar),
        'satis_fiyati': ozel_fiyat or str(stok.satis_fiyati),
        'kdv_orani': stok.kdv_orani,
        'para_birimi': {
            'kod': stok.para_birimi.kod,
            'sembol': stok.para_birimi.sembol
        },
        'secenekler': secenekler,
        'indirim_bilgisi': indirim_bilgisi
    }
    
    return JsonResponse(data)


@login_required
def fatura_pdf(request, pk):
    """Fatura PDF çıktısı"""
    fatura = get_object_or_404(Fatura, pk=pk, silindi=False)
    
    # PDF oluşturma kodu buraya gelecek (ReportLab veya WeasyPrint kullanılabilir)
    # Şimdilik sadece HTML olarak gösterelim
    return render(request, 'fatura/print.html', {'fatura': fatura})



@login_required
def fatura_detay(request, pk):
    # Detay yerine düzenlemeye yönlendir
    return redirect('fatura_duzenle', pk=pk)

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
    silinen_carihareketler = CariHareket.objects.filter(silindi=True)
    silinen_faturalar = Fatura.objects.filter(silindi=True)
    
    context = {
        'silinen_cariler': silinen_cariler,
        'silinen_gruplar': silinen_gruplar,
        'silinen_stoklar': silinen_stoklar,
        'silinen_carihareketler': silinen_carihareketler,
        'silinen_faturalar': silinen_faturalar,
        
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
    elif model_name == 'carihareket' or model_name == 'carihareketler':
        obj = get_object_or_404(CariHareket, pk=pk)
    elif model_name == 'fatura':
        obj = get_object_or_404(Fatura, pk=pk)
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
    elif model_name == 'carihareket' or model_name == 'carihareketler':
        obj = get_object_or_404(CariHareket, pk=pk)
    elif model_name == 'fatura':
        obj = get_object_or_404(Fatura, pk=pk)
    elif model_name == 'genelsecenek':
        obj = get_object_or_404(GenelStokSecenek, pk=pk)
    elif model_name == 'genelsecenekdeger':
        obj = get_object_or_404(GenelStokSecenekDeger, pk=pk)
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
        elif kategori == 'carihareket':  
            silinecekler = CariHareket.objects.filter(silindi=True)
            sayi = silinecekler.count()
            silinecekler.delete()
            messages.success(request, f'{sayi} adet cari hareket kaydı kalıcı olarak silindi!')
        elif kategori == 'fatura':  # YENİ
            silinecekler = Fatura.objects.filter(silindi=True)
            sayi = silinecekler.count()
            silinecekler.delete()
            messages.success(request, f'{sayi} adet fatura kalıcı olarak silindi!')
        else:
            messages.error(request, 'Geçersiz kategori!')
    
    return redirect('silinen_kayitlar')


@login_required
def stok_secenek_sil(request, pk):
    if request.method == 'POST':
        secenek = get_object_or_404(StokSecenek, pk=pk)
        secenek.soft_delete(request.user)
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

# yetkili_menu view'ını güncelle
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
        'genel_secenekler': GenelStokSecenek.objects.filter(silindi=False).count(),  # YENİ
    }
    return render(request, 'yetkili/menu.html', context)




@login_required
def genel_stok_secenek_deger_ekle(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Yetkiniz yok!'})
    
    if request.method == 'POST':
        secenek_id = request.POST.get('secenek_id')
        deger = request.POST.get('deger')
        fiyat_tipi = request.POST.get('fiyat_tipi')
        fiyat_degeri = request.POST.get('fiyat_degeri')
        varsayilan = request.POST.get('varsayilan') == 'true'
        
        try:
            secenek = GenelStokSecenek.objects.get(pk=secenek_id, silindi=False)
            
            # Son sıra numarasını bul
            son_sira = secenek.degerler.filter(silindi=False).aggregate(
                max_sira=models.Max('sira')
            )['max_sira'] or 0
            
            deger_obj = GenelStokSecenekDeger.objects.create(
                secenek=secenek,
                deger=deger,
                fiyat_tipi=fiyat_tipi,
                fiyat_degeri=fiyat_degeri,
                sira=son_sira + 1,
                varsayilan=varsayilan
            )
            
            return JsonResponse({'success': True, 'id': deger_obj.id})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False})

@login_required
def genel_stok_secenek_deger_sil(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Yetkiniz yok!'})
    
    if request.method == 'POST':
        deger = get_object_or_404(GenelStokSecenekDeger, pk=pk)
        deger.delete()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

@login_required
def genel_stok_secenek_deger_duzenle(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Yetkiniz yok!'})
    
    if request.method == 'POST':
        deger = get_object_or_404(GenelStokSecenekDeger, pk=pk)
        deger.deger = request.POST.get('deger')
        deger.fiyat_tipi = request.POST.get('fiyat_tipi')
        deger.fiyat_degeri = request.POST.get('fiyat_degeri')
        deger.varsayilan = request.POST.get('varsayilan') == 'true'
        deger.save()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

# Genel stok seçenek view'ları
@login_required
def genel_stok_secenek_list(request):
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok!')
        return redirect('anasayfa')
    
    secenekler = GenelStokSecenek.objects.filter(silindi=False).prefetch_related('degerler')
    return render(request, 'yetkili/genel_stok_secenek_list.html', {'secenekler': secenekler})

@login_required
def genel_secenek_kopyala(request, stok_id):
    if request.method == 'POST':
        stok = get_object_or_404(StokKart, pk=stok_id, silindi=False)
        genel_secenek_ids = request.POST.getlist('secenek_ids[]')
        
        # Mevcut seçenek başlıklarını al
        mevcut_basliklar = set(stok.secenekler.filter(silindi=False).values_list('baslik', flat=True))
        
        kopyalanan = 0
        atlanan = []
        
        for genel_secenek_id in genel_secenek_ids:
            genel_secenek = GenelStokSecenek.objects.get(pk=genel_secenek_id, silindi=False)
            
            # Aynı başlıkta seçenek var mı kontrol et
            if genel_secenek.baslik in mevcut_basliklar:
                atlanan.append(genel_secenek.baslik)
                continue
            
            # Stok seçeneği oluştur
            stok_secenek = StokSecenek.objects.create(
                stok=stok,
                baslik=genel_secenek.baslik,
                sira=genel_secenek.sira
            )
            
            # Değerleri kopyala
            for genel_deger in genel_secenek.degerler.filter(silindi=False):
                StokSecenekDeger.objects.create(
                    secenek=stok_secenek,
                    deger=genel_deger.deger,
                    fiyat_tipi=genel_deger.fiyat_tipi,
                    fiyat_degeri=genel_deger.fiyat_degeri,
                    sira=genel_deger.sira,
                    varsayilan=genel_deger.varsayilan
                )
            
            kopyalanan += 1
        
        if atlanan:
            message = f'{kopyalanan} seçenek eklendi. Zaten mevcut olanlar: {", ".join(atlanan)}'
        else:
            message = f'{kopyalanan} seçenek başarıyla eklendi!'
        
        return JsonResponse({
            'success': True,
            'message': message
        })
    
    return JsonResponse({'success': False})


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
    hareketler = CariHareket.objects.filter(silindi=False).select_related(
        'cari', 'para_birimi', 'kasa', 'banka', 'pos', 'olusturan'
    ).order_by('-tarih', '-id')
    
    # Filtreler
    tarih_bas = request.GET.get('tarih_bas')
    tarih_son = request.GET.get('tarih_son')
    cari_ara = request.GET.get('cari_ara')
    islem_tipi = request.GET.get('islem_tipi')
    hareket_yonu = request.GET.get('hareket_yonu')
    tutar_min = request.GET.get('tutar_min')
    tutar_max = request.GET.get('tutar_max')

    if tutar_min:
        try:
            hareketler = hareketler.filter(tutar__gte=Decimal(tutar_min))
        except:
            pass

    if tutar_max:
        try:
            hareketler = hareketler.filter(tutar__lte=Decimal(tutar_max))
        except:
            pass
    
    if tarih_bas:
        hareketler = hareketler.filter(tarih__date__gte=tarih_bas)
    if tarih_son:
        hareketler = hareketler.filter(tarih__date__lte=tarih_son)
    

    # Para birimi filtresi
    para_birimi = request.GET.get('para_birimi')
    if para_birimi:
        hareketler = hareketler.filter(para_birimi_id=para_birimi)

    # İşlemi yapan filtresi
    islem_yapan = request.GET.get('islem_yapan')
    if islem_yapan:
        hareketler = hareketler.filter(olusturan_id=islem_yapan)

    # Hesap filtresi
    hesap = request.GET.get('hesap')
    if hesap:
        if hesap.startswith('kasa-'):
            kasa_id = hesap.replace('kasa-', '')
            hareketler = hareketler.filter(kasa_id=kasa_id, islem_tipi='nakit')
        elif hesap.startswith('banka-'):
            banka_id = hesap.replace('banka-', '')
            hareketler = hareketler.filter(banka_id=banka_id, islem_tipi='banka')


    if cari_ara:
        hareketler = hareketler.filter(
            Q(cari__unvan__icontains=cari_ara) | 
            Q(cari__kod__icontains=cari_ara)
        )
    if islem_tipi:
        hareketler = hareketler.filter(islem_tipi=islem_tipi)
    if hareket_yonu:
        hareketler = hareketler.filter(hareket_yonu=hareket_yonu)
    

    

    # Bugünkü istatistikler
    bugun = timezone.now().date()
    bugunki_hareketler = CariHareket.objects.filter(
        silindi=False,
        tarih__date=bugun
    )
    
    bugunki_islem_sayisi = bugunki_hareketler.count()
    
    # TL bazında bugünkü tahsilat ve ödeme
    try:
        tl = ParaBirimi.objects.get(kod='TL')
        bugunki_tahsilat = bugunki_hareketler.filter(
            hareket_yonu='giris',
            para_birimi=tl
        ).aggregate(toplam=models.Sum('tutar'))['toplam'] or 0
        
        bugunki_odeme = bugunki_hareketler.filter(
            hareket_yonu='cikis',
            para_birimi=tl
        ).aggregate(toplam=models.Sum('tutar'))['toplam'] or 0
    except ParaBirimi.DoesNotExist:
        bugunki_tahsilat = 0
        bugunki_odeme = 0
    
    toplam_islem_sayisi = CariHareket.objects.filter(silindi=False).count()

    # Sayfalama için toplam hesapları al (sayfalamadan önce)
    
    
    toplam_giris = hareketler.filter(hareket_yonu='giris').aggregate(
        toplam=Sum('tutar')
    )['toplam'] or Decimal('0')
    
    toplam_cikis = hareketler.filter(hareket_yonu='cikis').aggregate(
        toplam=Sum('tutar')
    )['toplam'] or Decimal('0')
    
    # Sayfalama
    sayfa_boyutu = request.GET.get('sayfa_boyutu', '50')
    if sayfa_boyutu != 'all':
        paginator = Paginator(hareketler, int(sayfa_boyutu))
        page = request.GET.get('page')
        
        try:
            hareketler = paginator.page(page)
        except PageNotAnInteger:
            hareketler = paginator.page(1)
        except EmptyPage:
            hareketler = paginator.page(paginator.num_pages)
    
    context = {
        'hareketler': hareketler,
        'bugunki_islem_sayisi': bugunki_islem_sayisi,
        'bugunki_tahsilat': bugunki_tahsilat,
        'bugunki_odeme': bugunki_odeme,
        'toplam_islem_sayisi': toplam_islem_sayisi,
        'para_birimleri': ParaBirimi.objects.filter(silindi=False, aktif=True),
        'kullanicilar': User.objects.all().order_by('username'),
        'kasalar': Kasa.objects.filter(silindi=False, aktif=True),
        'bankalar': Banka.objects.filter(silindi=False, aktif=True),
        'hareketler': hareketler,
        'toplam_giris': toplam_giris,
        'toplam_cikis': toplam_cikis,
        
    }
    
    return render(request, 'cari_hareket/list.html', context)

@login_required
def cari_hareket_ekle(request, pk=None):
    if pk:
        hareket = get_object_or_404(CariHareket, pk=pk)
        title = 'Cari Hareket Düzenle'
    else:
        hareket = None
        title = 'Cari Hareket Ekle'
    
    if request.method == 'POST':
        form = CariHareketForm(request.POST, instance=hareket)
        if form.is_valid():
            hareket = form.save(commit=False)
            hareket.olusturan = request.user
            
            # Form clean metodunda zaten ayarlandı
            hareket.tutar = form.cleaned_data.get('tutar')
            hareket.hareket_yonu = form.cleaned_data.get('hareket_yonu')
            
            # Döviz işlemleri için
            doviz_kuru = request.POST.get('doviz_kuru')
            tl_tutar = request.POST.get('tl_tutar')
            
            # Döviz işlemi varsa
            if doviz_kuru and tl_tutar and hareket.para_birimi.kod != 'TL':
                try:
                    hareket.doviz_kuru = Decimal(doviz_kuru)
                    hareket.tl_karsiligi = Decimal(tl_tutar)
                    
                    # DÖVİZ İŞLEMİNDE KASA/BANKA DEĞİŞECEK!
                    if hareket.islem_tipi == 'nakit':
                        # TL kasası bul
                        tl = ParaBirimi.objects.get(kod='TL')
                        tl_kasa = Kasa.objects.filter(
                            para_birimi=tl,
                            aktif=True,
                            silindi=False
                        ).first()
                        if tl_kasa:
                            hareket.kasa = tl_kasa
                            
                    elif hareket.islem_tipi == 'banka':
                        # TL bankası bul
                        tl = ParaBirimi.objects.get(kod='TL')
                        tl_banka = Banka.objects.filter(
                            para_birimi=tl,
                            aktif=True,
                            silindi=False
                        ).first()
                        if tl_banka:
                            hareket.banka = tl_banka
                            
                except Exception as e:
                    print(f"Döviz işlemi hatası: {e}")
            
            hareket.save()
            
            # AJAX isteği ise JSON döndür
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'İşlem başarıyla kaydedildi!',
                    'hareket_id': hareket.id
                })
            else:
                messages.success(request, 'İşlem başarıyla kaydedildi!')
                return redirect('cari_hareket_list')
        else:
            # Form hataları varsa
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = []
                for field, error_list in form.errors.items():
                    for error in error_list:
                        errors.append(str(error))
                return JsonResponse({
                    'success': False,
                    'errors': ' '.join(errors)
                }, status=400)
    else:
        form = CariHareketForm(instance=hareket)
    
    # GET isteği veya form geçersizse template'i render et
    context = {
        'form': form,
        'title': title,
        'object': hareket,
        'doviz_kuru_str': str(hareket.doviz_kuru) if hareket and hareket.doviz_kuru else ''
    }
    return render(request, 'cari_hareket/form.html', context)


@login_required
def cari_hareket_sil(request, pk):
    if request.method == 'POST':
        try:
            hareket = get_object_or_404(CariHareket, pk=pk)
            hareket.soft_delete(request.user)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Hareket silindi!'})
            else:
                messages.success(request, 'Hareket silindi!')
                return redirect('cari_hareket_list')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': str(e)}, status=400)
            else:
                messages.error(request, 'Silme işlemi başarısız!')
                return redirect('cari_hareket_list')
    
    return redirect('cari_hareket_list')

@login_required
def cari_hareketler(request, cari_id):
    cari = get_object_or_404(CariKart, pk=cari_id, silindi=False)
    hareketler = cari.hareketler.filter(silindi=False).order_by('-tarih', '-id')
    
    # Özet bilgiler hesapla
    toplam_borc = hareketler.filter(hareket_yonu='cikis').aggregate(
        toplam=models.Sum('tutar')
    )['toplam'] or 0
    
    toplam_alacak = hareketler.filter(hareket_yonu='giris').aggregate(
        toplam=models.Sum('tutar')
    )['toplam'] or 0
    
    # Son hareket
    son_hareket = hareketler.first()
    
    context = {
        'cari': cari,
        'hareketler': hareketler,
        'toplam_borc': toplam_borc,
        'toplam_alacak': toplam_alacak,
        'son_hareket': son_hareket,
    }
    
    return render(request, 'cari_hareket/cari_hareketler.html', context)

# AJAX view'ları
@login_required
def cari_ara(request):
    q = request.GET.get('q', '')
    cariler = CariKart.objects.filter(
        silindi=False,
        aktif=True
    ).filter(
        Q(unvan__icontains=q) | Q(kod__icontains=q)
    )[:20]
    
    data = []
    for cari in cariler:
        data.append({
            'id': cari.id,
            'text': f"{cari.kod} - {cari.unvan}",
            'kod': cari.kod,
            'unvan': cari.unvan,
            'bakiye': str(cari.bakiye)
        })
    
    return JsonResponse({'results': data})


@login_required
def stok_ara(request):
    q = request.GET.get('q', '')
    stoklar = StokKart.objects.filter(
        silindi=False,
        aktif=True
    ).filter(
        Q(ad__icontains=q) | 
        Q(kod__icontains=q) | 
        Q(barkod__icontains=q)
    )[:20]
    
    data = []
    for stok in stoklar:
        data.append({
            'id': stok.id,
            'text': f"{stok.kod} - {stok.ad}",
            'kod': stok.kod,
            'ad': stok.ad,
            'barkod': stok.barkod or '',
            'birim': stok.get_birim_display(),
            'stok_miktari': str(stok.miktar),
            'satis_fiyati': str(stok.satis_fiyati),
            'para_birimi': stok.para_birimi.sembol
        })
    
    return JsonResponse({'results': data})

@login_required
def kasa_banka_getir(request):
    para_birimi_id = request.GET.get('para_birimi_id')
    islem_tipi = request.GET.get('islem_tipi')
    
    data = {'items': []}
    added_ids = set()  # Tekrar kontrolü için
    
    if para_birimi_id and islem_tipi:
        if islem_tipi == 'nakit':
            kasalar = Kasa.objects.filter(
                silindi=False,
                aktif=True,
                para_birimi_id=para_birimi_id
            ).order_by('kod')
            for kasa in kasalar:
                if kasa.id not in added_ids:
                    added_ids.add(kasa.id)
                    data['items'].append({
                        'id': kasa.id,
                        'text': f"{kasa.kod} - {kasa.ad}"
                    })
        elif islem_tipi == 'banka':
            bankalar = Banka.objects.filter(
                silindi=False,
                aktif=True,
                para_birimi_id=para_birimi_id
            ).order_by('kod')
            for banka in bankalar:
                if banka.id not in added_ids:
                    added_ids.add(banka.id)
                    data['items'].append({
                        'id': banka.id,
                        'text': f"{banka.kod} - {banka.ad}"
                    })
        elif islem_tipi == 'pos':
            poslar = Pos.objects.filter(
                silindi=False,
                aktif=True,
                banka__para_birimi_id=para_birimi_id
            ).order_by('kod')
            for pos in poslar:
                if pos.id not in added_ids:
                    added_ids.add(pos.id)
                    data['items'].append({
                        'id': pos.id,
                        'text': f"{pos.kod} - {pos.ad}"
                    })
    
    return JsonResponse(data)



@login_required
def cari_bakiye_detay(request):
    cari_id = request.GET.get('cari_id')
    
    if not cari_id:
        return JsonResponse({'success': False, 'error': 'Cari ID gerekli'})
    
    try:
        cari = CariKart.objects.get(id=cari_id)
        
        # Tüm para birimlerini al
        para_birimleri = ParaBirimi.objects.all()
        
        bakiyeler = []
        
        for pb in para_birimleri:
            # Bu para birimindeki toplam giriş ve çıkışları hesapla
            hareketler = CariHareket.objects.filter(
                cari=cari,
                para_birimi=pb,
                silindi=False  # Soft delete kontrolü
            )
            
            # Giriş hareketleri (cariden kasaya giriş = tahsilat)
            toplam_giris = hareketler.filter(hareket_yonu='giris').aggregate(
                toplam=Sum('tutar')
            )['toplam'] or 0
            
            # Çıkış hareketleri (kasadan cariye çıkış = ödeme)
            toplam_cikis = hareketler.filter(hareket_yonu='cikis').aggregate(
                toplam=Sum('tutar')
            )['toplam'] or 0
            
            bakiye = toplam_giris - toplam_cikis
            
            # Sadece hareketi olan para birimlerini göster
            if toplam_giris > 0 or toplam_cikis > 0:
                bakiyeler.append({
                    'para_birimi': f"{pb.kod} - {pb.ad}",
                    'toplam_giris': float(toplam_giris),
                    'toplam_cikis': float(toplam_cikis),
                    'bakiye': float(bakiye)
                })
        
        return JsonResponse({
            'success': True,
            'bakiyeler': bakiyeler
        })
        
    except CariKart.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Cari bulunamadı'})
    


@login_required
def genel_stok_secenek_ekle(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Yetkiniz yok!'})
    
    if request.method == 'POST':
        baslik = request.POST.get('baslik')
        
        if GenelStokSecenek.objects.filter(baslik=baslik, silindi=False).exists():
            return JsonResponse({'success': False, 'error': 'Bu başlıkta seçenek zaten var!'})
        
        secenek = GenelStokSecenek.objects.create(baslik=baslik)
        
        return JsonResponse({'success': True, 'id': secenek.id})
    
    return JsonResponse({'success': False})


@login_required
def genel_stok_secenek_sil(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Yetkiniz yok!'})
    
    if request.method == 'POST':
        secenek = get_object_or_404(GenelStokSecenek, pk=pk)
        secenek.delete()  # Kalıcı silme
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})
    

# views.py'ye ekle
@login_required
def genel_secenek_listesi_ajax(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Yetkiniz yok!'})
    
    secenekler = GenelStokSecenek.objects.filter(silindi=False).annotate(
        deger_sayisi=Count('degerler', filter=Q(degerler__silindi=False))
    )
    
    data = []
    for secenek in secenekler:
        data.append({
            'id': secenek.id,
            'baslik': secenek.baslik,
            'deger_sayisi': secenek.deger_sayisi
        })
    
    return JsonResponse({'success': True, 'secenekler': data})
    

@login_required
def cari_virman(request):
    if request.method == 'POST':
        form = CariVirmanForm(request.POST)
        if form.is_valid():
            # Form verilerini al
            tarih = form.cleaned_data['tarih']
            gonderen_cari = form.cleaned_data['gonderen_cari']
            gonderen_para_birimi = form.cleaned_data['gonderen_para_birimi']
            gonderen_tutar = form.cleaned_data['gonderen_tutar']
            alici_cari = form.cleaned_data['alici_cari']
            alici_para_birimi = form.cleaned_data['alici_para_birimi']
            alici_tutar = form.cleaned_data['alici_tutar']
            aciklama = form.cleaned_data['aciklama']
            
            # Döviz bilgilerini al
            gonderen_doviz_kuru = request.POST.get('gonderen_doviz_kuru')
            gonderen_doviz_tutar = request.POST.get('gonderen_doviz_tutar')
            alici_doviz_kuru = request.POST.get('alici_doviz_kuru')
            alici_doviz_tutar = request.POST.get('alici_doviz_tutar')
            
            try:
                # ALICI (ÜSTTEKİ) - GİRİŞ YAPAN
                if alici_doviz_kuru and alici_doviz_tutar:
                    # Döviz işlemi var
                    alici_hareket = CariHareket.objects.create(
                        tarih=tarih,
                        cari=alici_cari,
                        para_birimi=alici_para_birimi,
                        tutar=alici_tutar,  # Form'daki TL tutar
                        hareket_yonu='giris',
                        islem_tipi='virman',
                        aciklama=f'Virman - {gonderen_cari.unvan} carisinden. {aciklama}',
                        olusturan=request.user
                    )
                    if alici_para_birimi.kod != 'TL':
                        alici_hareket.doviz_kuru = Decimal(alici_doviz_kuru)
                        alici_hareket.tl_karsiligi = alici_tutar
                        alici_hareket.save()
                else:
                    # Normal işlem
                    alici_hareket = CariHareket.objects.create(
                        tarih=tarih,
                        cari=alici_cari,
                        para_birimi=alici_para_birimi,
                        tutar=alici_tutar,
                        hareket_yonu='giris',
                        islem_tipi='virman',
                        aciklama=f'Virman - {gonderen_cari.unvan} carisinden. {aciklama}',
                        olusturan=request.user
                    )
                
                # GÖNDEREN (ALTTAKİ) - ÇIKIŞ YAPAN
                # GÖNDEREN (ALTTAKİ) - ÇIKIŞ YAPAN
                if gonderen_doviz_kuru and gonderen_doviz_tutar and gonderen_para_birimi.kod != 'TL':
                    # Altta döviz seçili, üstte TL var
                    # gonderen_tutar = Form'dan gelen EUR tutarı
                    # gonderen_doviz_tutar = JavaScript'ten gelen TL karşılığı
                    gonderen_hareket = CariHareket.objects.create(
                        tarih=tarih,
                        cari=gonderen_cari,
                        para_birimi=gonderen_para_birimi,
                        tutar=gonderen_tutar,  # FORM'DAKİ TUTAR (EUR)
                        hareket_yonu='cikis',
                        islem_tipi='virman',
                        aciklama=f'Virman - {alici_cari.unvan} carisine. {aciklama}',
                        olusturan=request.user,
                        doviz_kuru=Decimal(gonderen_doviz_kuru),
                        tl_karsiligi=Decimal(gonderen_doviz_tutar)  # TL karşılığı
                    )
                    if gonderen_para_birimi.kod != 'TL':
                        gonderen_hareket.doviz_kuru = Decimal(gonderen_doviz_kuru)
                        gonderen_hareket.tl_karsiligi = alici_tutar  # Üstteki TL tutar
                        gonderen_hareket.save()
                else:
                    # Normal işlem
                    gonderen_hareket = CariHareket.objects.create(
                        tarih=tarih,
                        cari=gonderen_cari,
                        para_birimi=gonderen_para_birimi,
                        tutar=gonderen_tutar,
                        hareket_yonu='cikis',
                        islem_tipi='virman',
                        aciklama=f'Virman - {alici_cari.unvan} carisine. {aciklama}',
                        olusturan=request.user
                    )
                
                messages.success(request, 'Virman işlemi başarıyla tamamlandı!')
                return redirect('cari_hareket_list')
                
            except Exception as e:
                messages.error(request, f'Virman işlemi sırasında hata oluştu: {str(e)}')
                
    else:
        form = CariVirmanForm()
    
    return render(request, 'cari_hareket/virman_form.html', {
        'form': form,
        'title': 'Cari Virman İşlemi'
    })