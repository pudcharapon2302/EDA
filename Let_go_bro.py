# -*- coding: utf-8 -*-
"""READY.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1cRZgwcuWBwayiUmGD9AIx4q06nXpsriw
"""

import googlemaps
import pandas as pd
import time
import math
from geopy.distance import geodesic
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CafeAmazonScraperV3_CostSaver:
    def __init__(self, api_key):
        self.gmaps = googlemaps.Client(key=api_key)
        self.api_key = api_key

    def create_thailand_grid(self, grid_size_km=16):
        logger.info(f"กำลังสร้าง Grid Search ขนาด {grid_size_km}x{grid_size_km} กม. สำหรับประเทศไทย...")
        lat_min, lat_max = 5.6, 20.5
        lng_min, lng_max = 97.3, 105.7
        lat_step = grid_size_km / 111.0
        lng_step = grid_size_km / (111.0 * math.cos(math.radians(13)))
        grid_centers = []
        lat = lat_min
        while lat <= lat_max:
            lng = lng_min
            while lng <= lng_max:
                grid_centers.append((lat, lng))
                lng += lng_step
            lat += lat_step
        logger.info(f"สร้าง Grid สำเร็จ จำนวนทั้งหมด {len(grid_centers)} ช่อง")
        return grid_centers

    def search_cafe_amazon_in_thailand(self, grid_size_km=16):
        logger.info(f"เริ่มค้นหาสาขาด้วย Grid Search ขนาด {grid_size_km} กม. (โหมดประหยัด)...")

        grid_centers = self.create_thailand_grid(grid_size_km)
        radius_m = int(grid_size_km * 1000 / math.sqrt(2))

        all_cafes = []
        seen_place_ids = set()

        total_grids = len(grid_centers)
        for i, (lat, lng) in enumerate(grid_centers):
            logger.info(f"กำลังค้นหาใน Grid ที่ {i + 1}/{total_grids}...")
            try:
                page_result = self.gmaps.places_nearby(
                    location=(lat, lng),
                    radius=radius_m,
                    keyword='Cafe Amazon คาเฟ่ อเมซอน',
                    language='th'
                )
                all_cafes.extend(page_result.get('results', []))

                while 'next_page_token' in page_result:
                    time.sleep(2)
                    page_result = self.gmaps.places_nearby(page_token=page_result['next_page_token'])
                    all_cafes.extend(page_result.get('results', []))

            except Exception as e:
                logger.error(f"เกิดข้อผิดพลาดในการค้นหาที่ Grid ({lat}, {lng}): {e}")
                time.sleep(1)
                continue

        final_cafe_list = []
        for cafe in all_cafes:
            place_id = cafe.get('place_id')
            if place_id and place_id not in seen_place_ids:
                name = cafe.get('name', '').lower()
                if 'amazon' in name or 'อเมซอน' in name:
                    final_cafe_list.append(cafe)
                    seen_place_ids.add(place_id)

        logger.info(f"ค้นพบสาขา Cafe Amazon ที่ไม่ซ้ำกันทั้งหมด: {len(final_cafe_list)} สาขา")
        return final_cafe_list

    def get_place_details(self, place_id):
        try:
            # ลบ 'types' ออกจาก fields เพราะ Google Maps Places API ไม่รองรับแล้ว
            details = self.gmaps.place(place_id=place_id, fields=['name', 'formatted_address', 'geometry', 'rating', 'user_ratings_total', 'business_status'], language='th')
            return details.get('result')
        except Exception as e:
            logger.error(f"ไม่สามารถดึงข้อมูลรายละเอียดของ {place_id} ได้: {e}")
            return None

    def analyze_location_type(self, lat, lng):
        try:
            rev_geo = self.gmaps.reverse_geocode((lat, lng))
            if not rev_geo: return 'ไม่สามารถระบุได้'
            top_res = rev_geo[0]
            addr_comp = top_res.get('address_components', [])
            types = top_res.get('types', []) # types จาก reverse_geocode ยังใช้ได้อยู่
            for comp in addr_comp:
                if 'route' in comp.get('types', []):
                    road_name = comp.get('long_name', '').lower()
                    if any(x in road_name for x in ['ทางหลวง', 'highway', 'motorway', 'ถนนมิตรภาพ', 'ถนนสุขุมวิท', 'ถนนพหลโยธิน']):
                        return 'ติดถนนสายหลัก/ทางหลวง'
            if 'street_address' in types or 'route' in types: return 'ถนนสายรอง/ในเมือง'
            if 'sublocality' in types: return 'ย่านที่อยู่อาศัย/ในซอย'
            return 'พื้นที่ทั่วไป'
        except Exception as e:
            logger.error(f"ไม่สามารถวิเคราะห์ลักษณะทำเลได้: {e}")
            return 'ไม่สามารถระบุได้'

    def analyze_target_audience(self, cafe_summary, place_details): # รับ cafe_summary เพิ่มเข้ามา
        audience = set()
        
        # 1. ใช้ types จาก cafe_summary (จาก places_nearby) เป็นหลัก
        summary_types = cafe_summary.get('types', [])
        if any(t in summary_types for t in ['hospital', 'doctor', 'health', 'clinic']):
            audience.add('ผู้ป่วย/บุคลากรทางการแพทย์')
        if any(t in summary_types for t in ['school', 'university', 'college']):
            audience.add('นักเรียน/นักศึกษา')
        if any(t in summary_types for t in ['shopping_mall', 'department_store', 'store']):
            audience.add('นักช้อป')
        if 'gas_station' in summary_types:
            audience.add('ผู้ใช้รถยนต์/นักเดินทาง')
        if any(t in summary_types for t in ['train_station', 'bus_station', 'airport', 'transit_station']):
            audience.add('ผู้โดยสาร/นักท่องเที่ยว')
            
        # 2. ใช้ name และ formatted_address จาก place_details เป็นข้อมูลสำรอง/เสริม
        name = place_details.get('name', '').lower()
        address = place_details.get('formatted_address', '').lower()

        if not audience: # ถ้ายังไม่มีกลุ่มเป้าหมายจากการวิเคราะห์ types
            if any(k in name or k in address for k in ['โรงพยาบาล', 'รพ.', 'clinic', 'คลินิก', 'hospital']):
                audience.add('ผู้ป่วย/บุคลากรทางการแพทย์')
            if any(k in name or k in address for k in ['โรงเรียน', 'มหาลัย', 'university', 'school', 'college']):
                audience.add('นักเรียน/นักศึกษา')
            if any(k in name or k in address for k in ['ห้าง', 'mall', 'department store', 'shopping']):
                audience.add('นักช้อป')
            if any(k in name or k in address for k in ['ปตท', 'บางจาก', 'esso', 'shell', 'ปั๊ม', 'gas station']):
                audience.add('ผู้ใช้รถยนต์/นักเดินทาง')
            if any(k in name or k in address for k in ['สถานีรถไฟ', 'สถานีขนส่ง', 'สนามบิน', 'airport', 'bus terminal', 'train station']):
                audience.add('ผู้โดยสาร/นักท่องเที่ยว')

        return ', '.join(list(audience)) if audience else None # คืนค่า None ถ้าไม่สามารถระบุกลุ่มเป้าหมายได้

    def process_cafe_data(self, cafes):
        processed_data = []
        total_cafes = len(cafes)
        all_coords = [{'lat': c['geometry']['location']['lat'], 'lng': c['geometry']['location']['lng']} for c in cafes]
        logger.info(f"เริ่มประมวลผลข้อมูลรายละเอียด {total_cafes} สาขา...")
        for index, cafe_summary in enumerate(cafes): # เปลี่ยนชื่อตัวแปรจาก cafe_summary เป็น cafe_summary
            try:
                logger.info(f"ประมวลผลสาขาที่ {index + 1}/{total_cafes} - {cafe_summary.get('name')}")
                place_id = cafe_summary.get('place_id')
                details = self.get_place_details(place_id)
                if not details: continue
                lat = details['geometry']['location']['lat']
                lng = details['geometry']['location']['lng']
                min_distance, nearby_count_2km = float('inf'), 0
                for i, other_coord in enumerate(all_coords):
                    if i == index: continue
                    distance = geodesic((lat, lng), (other_coord['lat'], other_coord['lng'])).kilometers
                    if distance < min_distance: min_distance = distance
                    if distance <= 2: nearby_count_2km += 1
                
                # ส่ง cafe_summary เข้าไปใน analyze_target_audience
                target_audience = self.analyze_target_audience(cafe_summary, details)

                processed_data.append({
                    'ชื่อสาขา': details.get('name', 'N/A'),
                    'ที่อยู่': details.get('formatted_address', 'N/A'),
                    'ละติจูด': lat,
                    'ลองจิจูด': lng,
                    'คะแนนเฉลี่ย': details.get('rating', 0),
                    'จำนวนรีวิว': details.get('user_ratings_total', 0),
                    'ลักษณะทำเล': self.analyze_location_type(lat, lng),
                    'ประเภทกลุ่มเป้าหมาย': target_audience, # ใช้ค่าที่ได้จากการปรับปรุง
                    'จำนวนสาขาในรัศมี_2_กม': nearby_count_2km,
                    'ระยะห่างจากสาขาใกล้สุด_กม': round(min_distance, 2) if min_distance != float('inf') else 0,
                    'Place_ID': place_id
                })
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"เกิดข้อผิดพลาดในการประมวลผลสาขา {cafe_summary.get('place_id')}: {e}")
                continue
        return processed_data

    def save_to_csv(self, data, filename=None):
        if not filename: filename = f"cafe_amazon_thailand_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        if not data: logger.warning("ไม่มีข้อมูลสำหรับบันทึก"); return None
        try:
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"บันทึกข้อมูลสำเร็จ: {filename}")
            return filename
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการบันทึกไฟล์: {e}"); return None

    def run_full_scrape(self, output_filename=None, grid_size_km=16):
        logger.info(f"--- เริ่มการดึงข้อมูล Cafe Amazon (V3 - โหมดประหยัด) ---")
        cafes = self.search_cafe_amazon_in_thailand(grid_size_km=grid_size_km)

        if not cafes:
            logger.error("ไม่พบข้อมูลสาขา Cafe Amazon เลย")
            return None
        processed_data = self.process_cafe_data(cafes)
        filename = self.save_to_csv(processed_data, output_filename)
        return filename

# --- ตัวอย่างการใช้งาน ---
def main():
    # เปลี่ยน API_KEY เป็นคีย์ของคุณ
    API_KEY = "AIzaSyAJzaEOUtIRXZyS9WCUW4lc66-jdpZ-iS4" # ตัวอย่างคีย์ของคุณ

    scraper = CafeAmazonScraperV3_CostSaver(API_KEY)

    result_file = scraper.run_full_scrape(
        output_filename="cafe_amazon_thailand_data_costsaver_null_audience.csv", # เปลี่ยนชื่อไฟล์ output เพื่อแยกแยะ
        grid_size_km=16
    )
()
    if result_file:
        print(f"\nการดึงข้อมูลเสร็จสิ้น! ไฟล์ถูกบันทึกที่: {result_file}")
        print(f"ค่าใช้จ่ายโดยประมาณสำหรับการรันครั้งนี้อยู่ที่ ~ $280 USD (ก่อนหักเครดิตฟรี $200)")
    else:
        print("\nการดึงข้อมูลไม่สำเร็จ โปรดตรวจสอบ Log ด้านบน")

if __name__ == "__main__":
    main()