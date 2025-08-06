import requests
import xml.etree.ElementTree as ET
from django.core.cache import cache
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def doviz_kurlari(request):
    """TCMB'den resmi döviz kurlarını çeker"""
    
    # Cache'den kontrol et (30 dakika cache)
    kurlar = cache.get('doviz_kurlari')
    
    if not kurlar:
        try:
            # TCMB XML feed
            response = requests.get(
                'https://www.tcmb.gov.tr/kurlar/today.xml',
                timeout=5
            )
            
            if response.status_code == 200:
                # XML parse et
                root = ET.fromstring(response.content)
                
                kurlar = {}
                
                # USD ve EUR kurlarını bul
                for currency in root.findall('.//Currency'):
                    kod = currency.get('Kod')
                    
                    if kod == 'USD':
                        # Satış kurunu al
                        forex_selling = currency.find('ForexSelling')
                        if forex_selling is not None and forex_selling.text:
                            kurlar['USD'] = float(forex_selling.text)
                    
                    elif kod == 'EUR':
                        # Satış kurunu al
                        forex_selling = currency.find('ForexSelling')
                        if forex_selling is not None and forex_selling.text:
                            kurlar['EUR'] = float(forex_selling.text)
                
                # Cache'e kaydet (30 dakika)
                cache.set('doviz_kurlari', kurlar, 1800)

            else:
                kurlar = {'USD': None, 'EUR': None}
                
        except Exception as e:
            logger.error(f"TCMB döviz kuru çekme hatası: {str(e)}")
            kurlar = {'USD': None, 'EUR': None}
    
    return {
        'doviz_kurlari': kurlar
    }