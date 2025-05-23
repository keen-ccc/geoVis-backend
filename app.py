import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, render_template
import sqlite3
from flask_cors import CORS
import geopandas as gpd
import dask.dataframe as dd
import re
import math


app = Flask(__name__)
app.debug = True
CORS(app)
population_data = pd.read_csv('population_density_split.csv')
def get_db():
    conn = sqlite3.connect('geovis.sqlite')
    return conn

def cal_populationDensity(start_lon,start_lat,end_lon,end_lat):
    # 高德坐标转换为WGS84坐标
    start_lon,start_lat = gcj02_to_wgs84(start_lon,start_lat)
    end_lon,end_lat = gcj02_to_wgs84(end_lon,end_lat)
    # data = pd.read_csv('population_density_split.csv')
    # print("人口密度数据：",data.head())
    filter_data = population_data[(population_data['X'] >= start_lon) & (population_data['X'] <= end_lon) & (population_data['Y'] >= start_lat) & (population_data['Y'] <= end_lat)]
    print("人口密度数据：",filter_data)
    if filter_data.shape[0] == 0:
        return 0
    population_density = np.mean(filter_data['Z'])
    print("人口密度：",population_density)
    return population_density

def cal_housePrice(start_lon,start_lat,end_lon,end_lat):
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT * FROM houseprice WHERE lon BETWEEN {} AND {} AND lat BETWEEN {} AND {}".format(start_lon,end_lon,start_lat,end_lat)
    query_result = cur.execute(query)
    df = pd.DataFrame(query_result.fetchall(), columns=['cityname','zone','name','address','price','lon','lat'])
    # 计算网格内小区房价平均值
    mean_price = df['price'].mean()
    print("房价：",mean_price)
    # 如果为nan
    if np.isnan(mean_price):
        mean_price = 0
    return mean_price

def cal_poiDensity_poiDiversity(start_lon, start_lat, end_lon, end_lat,grid_size):
    conn = get_db()
    cur = conn.cursor()
    
    # 合并查询POI数量
    combined_query = """
    SELECT 'canyin' as type,  name, lon, lat, address FROM canyin WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'company' as type,  name, lon, lat, address FROM company WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'gouwu' as type,  name, lon, lat, address FROM mall WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'gdBank' as type, name, lon, lat, address FROM jpbank WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'express' as type, name, lon, lat, address  FROM express WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'yiliao' as type, name, lon, lat, address  FROM yiliao WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'wenhua' as type, name, lon, lat, address  FROM wenhua WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'zhusu' as type, name, lon, lat, address  FROM zhusu WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'zhengfu' as type, name, lon, lat, address  FROM zhengfu WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'yule' as type, name, lon, lat, address  FROM yule WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'qichexiaoshou' as type, name, lon, lat, address  FROM qichexiaoshou WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'qichefuwu' as type, name, lon, lat, address  FROM qichefuwu WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL 
    SELECT 'zhuzhai' as type, name, lon, lat, address  FROM qichefuwu WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    """
    
    params = (start_lon, end_lon, start_lat, end_lat) * 13
    combined_query_result = cur.execute(combined_query, params)
    combined_df = pd.DataFrame(combined_query_result.fetchall(), columns=[ 'type','name', 'lon', 'lat', 'address'])
    
    # 计算各类别POI数量
    # 计算每个类别的POI数量
    canyin_count = combined_df[combined_df['type'] == 'canyin'].shape[0]
    company_count = combined_df[combined_df['type'] == 'company'].shape[0]
    gouwu_count = combined_df[combined_df['type'] == 'mall'].shape[0]
    # jpbank_count = combined_df[combined_df['type'] == 'jpbank'].shape[0]
    # yzbank_count = combined_df[combined_df['type'] == 'yzbank'].shape[0]
    # bank_count = jpbank_count + yzbank_count
    bank_count = combined_df[combined_df['type'] == 'gdBank'].shape[0]
    express_count = combined_df[combined_df['type'] == 'express'].shape[0]
    yiliao_count = combined_df[combined_df['type'] == 'yiliao'].shape[0]
    wenhua_count = combined_df[combined_df['type'] == 'wenhua'].shape[0]
    zhusu_count = combined_df[combined_df['type'] == 'zhusu'].shape[0]
    zhengfu_count = combined_df[combined_df['type'] == 'zhengfu'].shape[0]
    yule_count = combined_df[combined_df['type'] == 'yule'].shape[0]
    qichexiaoshou_count = combined_df[combined_df['type'] == 'qichexiaoshou'].shape[0]
    qichefuwu_count = combined_df[combined_df['type'] == 'qichefuwu'].shape[0]
    zhuzhai_count = combined_df[combined_df['type'] == 'zhuzhai'].shape[0]
    
    # print("餐饮：",canyin_count)
    # print("企业：",company_count)
    # print("商场：",gouwu_count)
    # print("银行",bank_count)
    # print("物流",express_count)

    # 计算总数
    poi_count = combined_df.shape[0]
    # 计算密度
    # poi_density = poi_count / ((end_lon - start_lon) * (end_lat - start_lat))
    # 1平方千米
    # poi_density = poi_count / 1
    poi_density = poi_count / (grid_size * grid_size / 1000000)
    # 计算多样性
    # 如果除数为0
    if poi_count == 0:
        poi_diversity = 0
    else:
        poi_diversity = -sum([x / poi_count * np.log(x / poi_count) for x in [canyin_count, company_count, gouwu_count, bank_count,express_count,yiliao_count,wenhua_count,zhusu_count,zhengfu_count,yule_count,qichefuwu_count,qichexiaoshou_count,zhuzhai_count] if x != 0])
    print("网格POI数量：",poi_count)
    print("网格POI密度：",poi_density)
    print("网格POI多样性：",poi_diversity)

    return poi_density, poi_diversity


@app.route('/api/cal_score', methods=['POST'])
def cal_score():
    # 初始权重
    # populationWeight = 1 - 0.8673254174870703 = 0.1326745825129297
    # housePriceWeight = 1 - 0.5709951600935983 = 0.4290048399064017
    # poiDensityWeight = 1 - 0.6428892367629705 = 0.3571107632370295
    # poiDiversityWeight = 1 - 0.6915434317121325 = 0.3084565682878675
    data = request.get_json()
    gridID = data.get('gridID')
    start_lon = data.get('start_lon')
    start_lat = data.get('start_lat')
    end_lon = data.get('end_lon')
    end_lat = data.get('end_lat')
    populationWeight = data.get('populationWeight')
    housePriceWeight = data.get('housePriceWeight')
    poiDensityWeight = data.get('poiDensityWeight')
    poiDiversityWeight = data.get('poiDiversityWeight')
    sum_weight = data.get('sumWeight')
    grid_size = data.get('gridSize')
    print('--------------------------------------------------------')
    print(gridID,start_lon,start_lat,end_lon,end_lat,populationWeight,housePriceWeight,poiDensityWeight,poiDiversityWeight,sum_weight)

    # 确保所有参数都存在
    if None in [start_lon, start_lat, end_lon, end_lat, populationWeight, housePriceWeight, poiDensityWeight, poiDiversityWeight]:
        return jsonify({'error': 'Missing parameters'}), 400
    # sum_weight = 
    population_density = cal_populationDensity(start_lon,start_lat,end_lon,end_lat)
    house_price = cal_housePrice(start_lon,start_lat,end_lon,end_lat) 
    poi_density, poi_diversity = cal_poiDensity_poiDiversity(start_lon,start_lat,end_lon,end_lat,grid_size)
    # score = sum([population_density,house_price,poi_density, poi_diversity]) / sum_weight
    
    value = [population_density,house_price,poi_density, poi_diversity]
    # 归一化
    scale_population_density = (population_density) / 165134.45
    scale_house_price = (house_price) / 55852.33
    scale_poi_density = (poi_density) / 3000   # 1333
    scale_poi_diversity = (poi_diversity) / 2.1  # 1.55

    print("归一化后的指标值：",scale_population_density,scale_house_price,scale_poi_density,scale_poi_diversity)
    score = populationWeight/sum_weight * scale_population_density + housePriceWeight/sum_weight * scale_house_price + poiDensityWeight/sum_weight * scale_poi_density + poiDiversityWeight/sum_weight * scale_poi_diversity
    
    
    return jsonify({'value': value, 'score': score,'gridID':gridID})

# cal_populationDensity(103.55,30.55,103.56,30.56)


# 获取POI表格详情
@app.route('/api/getPOIDetail', methods=['POST'])
def getPOIDetail():
    data = request.get_json()
    type = data.get('type')
    start_lon = data.get('start_lon')
    start_lat = data.get('start_lat')
    end_lon = data.get('end_lon')
    end_lat = data.get('end_lat')
    conn = get_db()
    cur = conn.cursor()
    # 判断POI类型
    if type == '银行':
        table_name = 'gdBank'
    elif type == '物流':
        table_name = 'express'
    elif type == '餐饮':
        table_name = 'canyin'
    elif type == '企业':
        table_name = 'company'
    elif type == '购物':
        table_name = 'gouwu'
    elif type == '医疗':
        table_name = 'yiliao'
    elif type == '科教文化':
        table_name = 'wenhua'
    elif type == '住宿':
        table_name = 'zhusu'
    elif type == '政府机构':
        table_name = 'zhengfu'
    elif type == '娱乐':
        table_name = 'yule'
    elif type == '汽车销售':
        table_name = 'qichexiaoshou'
    elif type == '汽车服务':
        table_name = 'qichefuwu'
    elif type == '商务住宅':
        table_name = 'zhuzhai'
    
    query = "SELECT name,cityname,adname,address,lon,lat FROM {} WHERE lon BETWEEN {} AND {} AND lat BETWEEN {} AND {}".format(table_name,start_lon,end_lon,start_lat,end_lat)
    print("查询语句：",query)
    quere_result = cur.execute(query)
    df = pd.DataFrame(quere_result.fetchall(), columns=['name','cityname','adname','address','lon','lat'])
    # 拼接地址
    df['address'] = df['cityname'] + df['adname'] + df['address']
    df.drop(['cityname','adname'],axis=1,inplace=True)
    # 转换为对象数组
    table_result = df.to_dict(orient='records')
    # print(table_result)
    return jsonify(table_result)

# getPOIDetail('餐饮',102.26,27.92,102.27,27.91)

# 获取网格 市场经营主体 行业门类
@app.route('/api/getIndustry', methods=['POST'])
def getIndustry():
    data = request.get_json()
    start_lon = data.get('start_lon')
    start_lat = data.get('start_lat')
    end_lon = data.get('end_lon')
    end_lat = data.get('end_lat')
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT hyclass,hycode FROM entity WHERE lon BETWEEN {} AND {} AND lat BETWEEN {} AND {}".format(start_lon,end_lon,start_lat,end_lat)
    # query = "SELECT hyclass,hycode FROM entity limit 1000"
    query_result = cur.execute(query)
    # print("查询结果:",query_result.fetchall())
    df = pd.DataFrame(query_result.fetchall(), columns=['class','code'])
    industry_result = {
        "name":"经营主体",
        "children":[]
    }    
    # A-T 20个行业门类
    industry = ['农、林、牧、渔业','采矿业','制造业','电力、热力、燃气及水生产和供应业','建筑业','批发和零售业','交通运输、仓储和邮政业','住宿和餐饮业','信息传输、软件和信息技术服务业','金融业','房地产业','租赁和商务服务业','科学研究和技术服务业','水利、环境和公共设施管理业','居民服务、修理和其他服务业','教育','卫生和社会工作','文化、体育和娱乐业','公共管理、社会保障和社会组织','国际组织']
    # 根据行业代码 统计每个行业下的每个大类的数量
    for i in range(1,21):
        # 用i表示字母
        data = df[df['class'] == chr(64+i)]
        industry_result["children"].append({
                "name":industry[i-1],
                "children":[
                ]
        })
        # 如果i为1
        if i == 1:
            # 统计第一位数字为1-5的数量
            category = data['code'].apply(lambda x: x[0]).value_counts()
            for j in list(category.index):
                industry_result["children"][-1]["children"].append({
                    "name":j,
                    "value":int(category[j])
                })
        # 如果i为2
        elif i == 2:
            # 初始化计数字典
            count_3_digits = {}
            count_4_digits = {}
            #如果code为3位 统计第一位数字为6-9的数量
            # 遍历code
            for code in data['code']:
                # print(code,len(code))
                if len(code) == 3 and code[0] in ['6', '7', '8', '9']:
                    # 取第一位字符
                    first_digit = code[0]
                    # 计数
                    if first_digit in count_3_digits:
                        count_3_digits[first_digit] += 1
                    else:
                        count_3_digits[first_digit] = 1
                elif len(code) == 4:
                    # 取前两位字符
                    first_two_digits = code[:2]
                    # 计数
                    if first_two_digits in count_4_digits:
                        count_4_digits[first_two_digits] += 1
                    else:
                        count_4_digits[first_two_digits] = 1
            # 合并计数结果
            count_3_digits.update(count_4_digits)
            # print(count_3_digits)
            for j in count_3_digits:
                industry_result["children"][-1]["children"].append({
                    "name":j,
                    "value":int(count_3_digits[j])
                })
        # 其余门类 
        else:
            category = data['code'].apply(lambda x: x[:2]).value_counts()
            for j in list(category.index):
                industry_result["children"][-1]["children"].append({
                    "name":j,
                    "value":int(category[j])
                })
    # print("tree 数据：",industry_result)
    return jsonify(industry_result)

def simplify_businessscope(scope):
    # 删除括号内的文字（中英文）
    scope = re.sub(r'\（.*?\）', '', scope)
    scope = re.sub(r'\(.*?\)', '', scope)
    # 保留第二个分号前的内容
    parts = scope.split('；')
    if len(parts) >= 2:
        scope = '；'.join(parts[:2])
    # 删除多余的空格和分号
    # scope = scope.replace('；', '； ').strip()
    return scope

# 获取网格内实体详情
@app.route('/api/getIndustryDetail', methods=['POST'])
def getIndustryDetail():
    data = request.get_json()
    start_lon = data.get('start_lon')
    start_lat = data.get('start_lat')
    end_lon = data.get('end_lon')
    end_lat = data.get('end_lat')
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT name,address,businessscope,hyclass,hycode FROM entity WHERE lon BETWEEN {} AND {} AND lat BETWEEN {} AND {}".format(start_lon,end_lon,start_lat,end_lat)
    # query = "SELECT name,address,businessscope FROM entity limit 100"
    query_result = cur.execute(query)
    df = pd.DataFrame(query_result.fetchall(),columns=['name','address','businessscope','hyclass','hycode'])
    # 简化经营范围
    df['businessscope'] = df['businessscope'].apply(simplify_businessscope)
    # 行业门类映射成文字 A-T
    industry = ['农、林、牧、渔业','采矿业','制造业','电力、热力、燃气及水生产和供应业','建筑业','批发和零售业','交通运输、仓储和邮政业','住宿和餐饮业','信息传输、软件和信息技术服务业','金融业','房地产业','租赁和商务服务业','科学研究和技术服务业','水利、环境和公共设施管理业','居民服务、修理和其他服务业','教育','卫生和社会工作','文化、体育和娱乐业','公共管理、社会保障和社会组织','国际组织']
    df['hyclass'] = df['hyclass'].apply(lambda x: industry[ord(x)-65])
    df['hycode'] = df['hycode'].apply(lambda x:x.split('.')[0])
    # print(df)
    entity_result = df.to_dict(orient='records')
    # print("实体表格：",entity_result)
    return entity_result

# getIndustryDetail(102.26,27.92,102.27,27.91)

# 高德坐标系(GCJ-02)转换为WGS84坐标系
def gcj02_to_wgs84(lng, lat):
    def transformlat(lng, lat):
        ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * math.sqrt(abs(lng))
        ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lat * math.pi) + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(lat / 12.0 * math.pi) + 320 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
        return ret

    def transformlng(lng, lat):
        ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * math.sqrt(abs(lng))
        ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lng * math.pi) + 40.0 * math.sin(lng / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(lng / 12.0 * math.pi) + 300.0 * math.sin(lng / 30.0 * math.pi)) * 2.0 / 3.0
        return ret

    def out_of_china(lng, lat):
        if lng < 72.004 or lng > 137.8347:
            return True
        if lat < 0.8293 or lat > 55.8271:
            return True
        return False

    if out_of_china(lng, lat):
        return lng, lat

    dlat = transformlat(lng - 105.0, lat - 35.0)
    dlng = transformlng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - 0.00669342162296594323 * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((6335552.717000426 / (magic * sqrtmagic)) * math.pi)
    dlng = (dlng * 180.0) / ((6378245.0 / sqrtmagic) * math.cos(radlat) * math.pi)
    mglat = lat + dlat
    mglng = lng + dlng
    return lng * 2 - mglng, lat * 2 - mglat


if __name__ == '__main__':
    app.run()