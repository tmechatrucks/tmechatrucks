#!/usr/bin/env python3
"""Generate crawlable T-MechaTrucks product pages from the public Supabase catalog.
Run from the website root: python build_product_pages.py
Only reads public_products; never changes Supabase data or stock.
"""
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
SITE = 'https://www.tmechatrucks.com'
SUPABASE_URL = 'https://ivyzjzbtdlphjaeywtxa.supabase.co'
PUBLIC_KEY = 'sb_publishable_8uDL-s41xR7B7KHlfWCovA_v7ixrNAP'
FIELDS = 'id,sku,name,description,image_url,unit_price_incl_vat,vat_rate,is_active,manufacturer,manufacturer_part_number,oe_numbers,fitment_notes'

def fetch_products():
    rows = []
    offset = 0
    while True:
        params = urllib.parse.urlencode({'select':FIELDS, 'is_active':'eq.true', 'order':'name.asc', 'limit':'500', 'offset':str(offset)})
        request = urllib.request.Request(f'{SUPABASE_URL}/rest/v1/public_products?{params}', headers={'apikey':PUBLIC_KEY, 'Authorization':f'Bearer {PUBLIC_KEY}', 'Accept':'application/json'})
        with urllib.request.urlopen(request, timeout=40) as response:
            page = json.load(response)
        if not isinstance(page, list):
            raise ValueError('Unexpected Supabase response')
        rows.extend(page)
        if len(page) < 500:
            return rows
        offset += len(page)

def esc(value):
    return html.escape(str(value or ''), quote=True)

def slug(product):
    # SKU is unique and stable; never use an editable product name for the URL.
    safe = re.sub(r'[^a-z0-9]+', '-', str(product['sku']).lower()).strip('-')
    if not safe:
        raise ValueError('Product has no valid SKU')
    return safe

def number(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None

def render(product):
    name = str(product.get('name') or 'Truck spare part')
    sku = str(product['sku'])
    part = str(product.get('manufacturer_part_number') or '').strip()
    brand = str(product.get('manufacturer') or '').strip()
    desc = str(product.get('description') or f'Ask T-MechaTrucks & Parts Ltd in Kigali, Rwanda about {name}.')
    img = str(product.get('image_url') or '').strip()
    url = f'{SITE}/products/{slug(product)}.html'
    gross = number(product.get('unit_price_incl_vat'))
    vat = number(product.get('vat_rate'))
    if vat is None: vat = Decimal('0.18')
    if vat > 1: vat = vat / 100
    excl = (gross / (Decimal(1) + vat)).quantize(Decimal('1'), rounding=ROUND_HALF_UP) if gross is not None else None
    title = f'{name} | Buy Truck Parts in Rwanda | T-MechaTrucks'
    meta = (f'{name}. SKU {sku}. Genuine compatibility must be confirmed. Enquire with T-MechaTrucks & Parts Ltd, Kigali, Rwanda.')[:155]
    product_schema = {'@context':'https://schema.org','@type':'Product','name':name,'sku':sku,'description':desc,'url':url}
    if brand: product_schema['brand'] = {'@type':'Brand','name':brand}
    if part: product_schema['mpn'] = part
    if img: product_schema['image'] = [img]
    if gross is not None and gross > 0:
        product_schema['offers'] = {'@type':'Offer','url':url,'priceCurrency':'RWF','price':str(gross),'seller':{'@type':'Organization','name':'T-MechaTrucks & Parts Ltd','url':SITE},'itemCondition':'https://schema.org/NewCondition'}
        # Do not claim InStock: is_active means publicly listed, not confirmed inventory.
    org_schema = {'@context':'https://schema.org','@type':'Organization','name':'T-MechaTrucks & Parts Ltd','url':SITE,'address':{'@type':'PostalAddress','addressLocality':'Kigali','addressCountry':'RW'}}
    specs = ''.join(f'<li>{esc(label)}: {esc(value)}</li>' for label,value in [('SKU',sku),('Manufacturer part number',part),('Manufacturer',brand)] if value)
    image_tag = f'<img class="photo" src="{esc(img)}" alt="{esc(name)}" loading="eager">' if img else '<div class="photo missing">Product image not available</div>'
    price_tag = f'<p class="price">{gross:,.0f} RWF <small>(including VAT)</small></p><p>Price excluding VAT: {excl:,.0f} RWF</p>' if gross is not None and gross > 0 else '<p>Contact us for pricing.</p>'
    note = '<p class="note">Product compatibility and availability must be confirmed by our team before ordering.</p>'
    # WhatsApp inquiry without asserting availability.
    message = urllib.parse.quote(f'Hello T-MechaTrucks, please confirm availability and compatibility for {name} (SKU: {sku}).')
    schema = json.dumps([product_schema, org_schema], ensure_ascii=False).replace('<','\\u003c')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(meta)}">
<link rel="canonical" href="{esc(url)}"><link rel="icon" href="../images/logo.webp">
<meta property="og:type" content="product"><meta property="og:title" content="{esc(name)}"><meta property="og:description" content="{esc(meta)}"><meta property="og:url" content="{esc(url)}">
{f'<meta property="og:image" content="{esc(img)}">' if img else ''}
<script type="application/ld+json">{schema}</script>
<style>body{{margin:0;background:#f4f7fb;color:#172638;font:16px/1.6 Arial,sans-serif}}header,footer{{background:#082b50;color:white;padding:20px max(18px,calc((100vw - 1100px)/2))}}header a,footer a{{color:white}}main{{max-width:1100px;margin:30px auto;padding:0 18px}}.layout{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px;align-items:start}}.photo{{width:100%;max-height:460px;object-fit:contain;background:white;border-radius:14px;padding:16px;box-sizing:border-box}}.missing{{min-height:200px;display:grid;place-items:center}}.info{{background:white;padding:24px;border-radius:14px}}h1{{font-size:clamp(24px,3vw,35px);line-height:1.25}}.price{{font-size:24px;font-weight:800;color:#082b50}}small{{font-size:13px;font-weight:400}}.btn{{display:inline-block;background:#c49a32;color:#082b50;text-decoration:none;padding:12px 18px;border-radius:8px;font-weight:bold}}.note{{color:#536477}}@media(max-width:700px){{.layout{{grid-template-columns:1fr}}.info{{padding:18px}}}}</style>
</head><body><header><a href="../index.html">T-MechaTrucks &amp; Parts Ltd</a> &nbsp; | &nbsp; <a href="../new-product.html">All New Spare Parts</a></header>
<main><nav aria-label="Breadcrumb"><a href="../index.html">Home</a> / <a href="../new-product.html">New Spare Parts</a> / {esc(sku)}</nav>
<div class="layout"><div>{image_tag}</div><article class="info"><h1>{esc(name)}</h1><ul>{specs}</ul><p>{esc(desc)}</p>{price_tag}{note}<a class="btn" href="https://wa.me/250799908714?text={message}">Enquire on WhatsApp</a><p><a href="../new-product.html">Browse all products</a></p></article></div></main>
<footer>Kabutare, Rusororo, Gasabo, Kigali, Rwanda · T-MechaTrucks &amp; Parts Ltd</footer></body></html>'''

def main():
    try:
        products = fetch_products()
    except Exception as exc:
        print(f'ERROR: Could not read public products: {exc}', file=sys.stderr)
        sys.exit(1)
    if not products:
        print('ERROR: No public products returned; existing pages left unchanged.', file=sys.stderr)
        sys.exit(1)
    seen = set()
    pages = {}
    for product in products:
        try:
            s = slug(product)
            if s in seen: raise ValueError(f'Duplicate SKU slug: {s}')
            seen.add(s)
            pages[f'{s}.html'] = render(product)
        except Exception as exc:
            print(f'ERROR: Invalid product {product.get("sku")}: {exc}', file=sys.stderr)
            sys.exit(1)
    folder = ROOT / 'products'
    folder.mkdir(exist_ok=True)
    for filename, content in pages.items():
        (folder / filename).write_text(content, encoding='utf-8')
    # Remove only generated pages from prior builds, not unrelated files.
    marker = ROOT / '.generated-product-pages.json'
    if marker.exists():
        old = json.loads(marker.read_text(encoding='utf-8'))
        for filename in old:
            if filename not in pages and re.fullmatch(r'[a-z0-9-]+\.html', filename):
                (folder / filename).unlink(missing_ok=True)
    marker.write_text(json.dumps(sorted(pages), indent=2), encoding='utf-8')
    today = datetime.now(timezone.utc).date().isoformat()
    links = '\n'.join(f'  <url><loc>{SITE}/products/{filename}</loc><lastmod>{today}</lastmod></url>' for filename in sorted(pages))
    (ROOT / 'sitemap-products.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+links+'\n</urlset>\n', encoding='utf-8')
    print(f'Generated {len(pages)} public product pages in products/ and sitemap-products.xml')
    print('Upload generated pages and submit sitemap-products.xml once in Google Search Console.')

if __name__ == '__main__': main()
