from flask import Flask, render_template, request, jsonify, send_file
import qrcode
import io
import os
from datetime import datetime
import sxtwl
import pytz
import logging

app = Flask(__name__, 
            template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 在生产环境中禁用调试模式
app.config['DEBUG'] = False

# Print template folder path for debugging
print(f"Template folder path: {app.template_folder}")

# 天干
HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
# 地支
EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
# 五行
FIVE_ELEMENTS = {
    "金": {
        "numbers": [4, 9],
        "colors": ["白色", "银色", "金色"],
        "colors_en": ["White", "Silver", "Gold"],
        "element_en": "Metal"
    },
    "木": {
        "numbers": [3, 8],
        "colors": ["绿色", "青色"],
        "colors_en": ["Green", "Cyan"],
        "element_en": "Wood"
    },
    "水": {
        "numbers": [1, 6],
        "colors": ["黑色", "蓝色"],
        "colors_en": ["Black", "Blue"],
        "element_en": "Water"
    },
    "火": {
        "numbers": [2, 7],
        "colors": ["红色", "紫色", "橙色"],
        "colors_en": ["Red", "Purple", "Orange"],
        "element_en": "Fire"
    },
    "土": {
        "numbers": [5, 0],
        "colors": ["黄色", "棕色", "米色"],
        "colors_en": ["Yellow", "Brown", "Beige"],
        "element_en": "Earth"
    }
}

# 天干五行对应
STEMS_TO_ELEMENTS = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水"
}

# 地支五行对应
BRANCHES_TO_ELEMENTS = {
    "子": "水", "丑": "土", "寅": "木",
    "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金",
    "酉": "金", "戌": "土", "亥": "水"
}

def get_heavenly_stem_year(year):
    return HEAVENLY_STEMS[(year - 4) % 10]

def get_earthly_branch_year(year):
    return EARTHLY_BRANCHES[(year - 4) % 12]

def get_bazi(year, month, day, hour):
    # 简化版八字计算
    year_stem = get_heavenly_stem_year(year)
    year_branch = get_earthly_branch_year(year)
    
    # 月干支计算（简化）
    month_stem = HEAVENLY_STEMS[(year % 5 * 2 + month) % 10]
    month_branch = EARTHLY_BRANCHES[month - 1]
    
    # 日干支计算（简化）
    day_stem = HEAVENLY_STEMS[day % 10]
    day_branch = EARTHLY_BRANCHES[day % 12]
    
    # 时干支计算（简化）
    hour_stem = HEAVENLY_STEMS[hour % 10]
    hour_branch = EARTHLY_BRANCHES[(hour // 2) % 12]
    
    return {
        "year": (year_stem, year_branch),
        "month": (month_stem, month_branch),
        "day": (day_stem, day_branch),
        "hour": (hour_stem, hour_branch)
    }

def analyze_five_elements(bazi):
    elements_count = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
    
    # 统计八字中各五行的数量
    for pillar in bazi.values():
        stem, branch = pillar
        elements_count[STEMS_TO_ELEMENTS[stem]] += 1
        elements_count[BRANCHES_TO_ELEMENTS[branch]] += 1
    
    # 找出最弱的五行作为喜用神
    lucky_element = min(elements_count.items(), key=lambda x: x[1])[0]
    return lucky_element

def get_lucky_numbers_and_colors(lucky_element):
    element_info = FIVE_ELEMENTS[lucky_element]
    return {
        "numbers": element_info["numbers"],
        "colors": element_info["colors"],
        "colors_en": element_info["colors_en"],
        "element": lucky_element,
        "element_en": element_info["element_en"]
    }

def get_gan_zhi(day):
    """Convert lunar date components to Heavenly Stems and Earthly Branches"""
    gan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    zhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    
    # 获取干支序号
    year_gz = day.getYearGZ(False)  # 参数表示是否以春节为界
    month_gz = day.getMonthGZ()
    day_gz = day.getDayGZ()
    
    # 获取天干和地支的数值
    year_gan = year_gz.tg  # 天干
    year_zhi = year_gz.dz  # 地支
    month_gan = month_gz.tg
    month_zhi = month_gz.dz
    day_gan = day_gz.tg
    day_zhi = day_gz.dz
    
    # 组合干支
    year_gz = f"{gan[year_gan]}{zhi[year_zhi]}"
    month_gz = f"{gan[month_gan]}{zhi[month_zhi]}"
    day_gz = f"{gan[day_gan]}{zhi[day_zhi]}"
    
    return year_gz, month_gz, day_gz

def get_hour_gz(hour, day_gan):
    """Calculate hour's Heavenly Stem and Earthly Branch"""
    gan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    zhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    
    hour_zhi_index = hour // 2
    day_gan_index = gan.index(day_gan)
    hour_gan_base = (day_gan_index * 2) % 10
    hour_gan_index = (hour_gan_base + hour_zhi_index) % 10
    
    return f"{gan[hour_gan_index]}{zhi[hour_zhi_index]}"

def get_element_from_gz(year_gz, month_gz, day_gz, hour_gz):
    """Determine the dominant element based on the BaZi"""
    elements = {
        '甲': 'Wood', '乙': 'Wood',
        '丙': 'Fire', '丁': 'Fire',
        '戊': 'Earth', '己': 'Earth',
        '庚': 'Metal', '辛': 'Metal',
        '壬': 'Water', '癸': 'Water'
    }
    
    element_count = {'Wood': 0, 'Fire': 0, 'Earth': 0, 'Metal': 0, 'Water': 0}
    
    # Count elements from heavenly stems
    for gz in [year_gz[0], month_gz[0], day_gz[0], hour_gz[0]]:
        element_count[elements[gz]] += 2
    
    # Simplified counting from earthly branches
    branch_elements = {
        '子': 'Water', '丑': 'Earth', '寅': 'Wood',
        '卯': 'Wood', '辰': 'Earth', '巳': 'Fire',
        '午': 'Fire', '未': 'Earth', '申': 'Metal',
        '酉': 'Metal', '戌': 'Earth', '亥': 'Water'
    }
    
    for gz in [year_gz[1], month_gz[1], day_gz[1], hour_gz[1]]:
        element_count[branch_elements[gz]] += 1
    
    dominant_element = max(element_count.items(), key=lambda x: x[1])[0]
    
    element_map = {
        'Wood': ('木', 'Wood'),
        'Fire': ('火', 'Fire'),
        'Earth': ('土', 'Earth'),
        'Metal': ('金', 'Metal'),
        'Water': ('水', 'Water')
    }
    
    return element_map[dominant_element]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        logger.debug(f"Received data: {data}")
        
        # 获取输入数据
        birth_date = datetime.strptime(data['date'], '%Y-%m-%d')
        birth_hour = int(data['hour'])
        
        logger.debug(f"Parsed date: {birth_date}, hour: {birth_hour}")
        
        # Convert to lunar calendar using sxtwl
        lunar = sxtwl.fromSolar(birth_date.year, birth_date.month, birth_date.day)
        
        # Get BaZi components
        year_gz, month_gz, day_gz = get_gan_zhi(lunar)
        hour_gz = get_hour_gz(birth_hour, day_gz[0])
        
        # Calculate dominant element
        element_cn, element_en = get_element_from_gz(year_gz, month_gz, day_gz, hour_gz)
        
        # 根据五行获取幸运数字和颜色
        element_info = FIVE_ELEMENTS[element_cn]
        lucky_numbers = element_info["numbers"]
        colors_cn = element_info["colors"]
        colors_en = element_info["colors_en"]
        
        bazi = {
            'year': year_gz,
            'month': month_gz,
            'day': day_gz,
            'hour': hour_gz,
            'lunar_date': f"{lunar.getLunarYear()}年{lunar.getLunarMonth()}月{lunar.getLunarDay()}日"
        }
        
        return jsonify({
            'element': element_cn,
            'element_en': element_en,
            'numbers': lucky_numbers,
            'colors': colors_cn,
            'colors_en': colors_en,
            'bazi': bazi
        })
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/qr')
def generate_qr():
    """Generate QR code for the website"""
    try:
        # Get the current URL
        url = request.url_root
        
        # Create QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return send_file(img_bytes, mimetype='image/png')
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()

# 为 Vercel 添加必要的 WSGI 应用程序对象
app = app 
