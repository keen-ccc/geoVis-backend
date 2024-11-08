import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, render_template
import sqlite3


app = Flask(__name__)

def get_db():
    conn = sqlite3.connect('geovis.sqlite')
    return conn

def cal_populationDensity(start_lon,start_lat,end_lon,end_lat):
    data = pd.read_csv('population_density.csv')
    data = data[(data['X'] >= start_lon) & (data['X'] <= end_lon) & (data['Y'] >= end_lat) & (data['Y'] <= start_lat)]
    population_density = np.mean(data['Z'])
    print(population_density)
    return population_density

def cal_housePrice(start_lon,start_lat,end_lon,end_lat):
    # 非法检测
    # 
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT * FROM houseprice WHERE lon BETWEEN {} AND {} AND lat BETWEEN {} AND {}".format(start_lon,end_lon,end_lat,start_lat)
    query_result = cur.execute(query)
    df = pd.DataFrame(query_result.fetchall(), columns=['cityname','zone','name','address','price','lon','lat'])
    # 计算网格内小区房价平均值
    mean_price = df['price'].mean()
    # print(mean_price)
    return mean_price

def cal_poiDensity_poiDiversity(start_lon, start_lat, end_lon, end_lat):
    conn = get_db()
    cur = conn.cursor()
    
    # 合并查询餐饮、企业、商场和银行POI数量
    combined_query = """
    SELECT 'canyin' as type,  name, lon, lat, address FROM canyin WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'company' as type,  name, lon, lat, address FROM company WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'mall' as type,  name, lon, lat, address FROM mall WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'jpbank' as type, name, lon, lat, address FROM jpbank WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    UNION ALL
    SELECT 'yzbank' as type, name, lon, lat, address  FROM yzbank WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
    """
    
    params = (start_lon, end_lon, end_lat, start_lat) * 5
    combined_query_result = cur.execute(combined_query, params)
    combined_df = pd.DataFrame(combined_query_result.fetchall(), columns=[ 'type','name', 'lon', 'lat', 'address'])
    
    # 计算各类别POI数量
    # 计算每个类别的POI数量
    canyin_count = combined_df[combined_df['type'] == 'canyin'].shape[0]
    company_count = combined_df[combined_df['type'] == 'company'].shape[0]
    mall_count = combined_df[combined_df['type'] == 'mall'].shape[0]
    jpbank_count = combined_df[combined_df['type'] == 'jpbank'].shape[0]
    yzbank_count = combined_df[combined_df['type'] == 'yzbank'].shape[0]
    bank_count = jpbank_count + yzbank_count
    
    print(canyin_count)
    print(company_count)
    print(mall_count)
    print(bank_count)

    # 计算总数
    poi_count = combined_df.shape[0]
    # 计算密度
    poi_density = poi_count / ((end_lon - start_lon) * (end_lat - start_lat))
    # 计算多样性
    poi_diversity = -sum([x / poi_count * np.log(x / poi_count) for x in [canyin_count, company_count, mall_count, bank_count]])
    print("网格POI数量：",poi_count)
    print("网格POI密度：",poi_density)
    print("网格POI多样性：",poi_diversity)

    return poi_density, poi_diversity

# def cal_weight():
#     # 计算四个指标的权重
    

def cal_score(start_lon,start_lat,end_lon,end_lat):
    # sum_weight = 
    population_density = cal_populationDensity(start_lon,start_lat,end_lon,end_lat)
    house_price = cal_housePrice(start_lon,start_lat,end_lon,end_lat) 
    poi_density, poi_diversity = cal_poiDensity_poiDiversity(start_lon,start_lat,end_lon,end_lat)
    # score = sum([population_density,house_price,poi_density, poi_diversity]) / sum_weight



# cal_populationDensity(103.55,30.55,103.56,30.56)

# 获取POI表格详情
def getPOIDetail(type,start_lon,start_lat,end_lon,end_lat):
    conn = get_db()
    cur = conn.cursor()
    # 判断POI类型
    if type == '银行':
        table_name = 'jpbank'
    elif type == '物流':
        table_name = 'wuliu'
    elif type == '餐饮':
        table_name = 'canyin'
    elif type == '企业':
        table_name = 'company'
    elif type == '商场':
        table_name = 'mall'
    
    query = "SELECT name,cityname,adname,address FROM {} WHERE lon BETWEEN {} AND {} AND lat BETWEEN {} AND {}".format(table_name,start_lon,end_lon,end_lat,start_lat)
    quere_result = cur.execute(query)
    df = pd.DataFrame(quere_result.fetchall(), columns=['name','cityname','adname','address'])
    # 拼接地址
    df['address'] = df['cityname'] + df['adname'] + df['address']
    df.drop(['cityname','adname'],axis=1,inplace=True)
    # 转换为对象数组
    table_result = df.to_dict(orient='records')
    # print(table_result)
    return table_result

# getPOIDetail('餐饮',102.26,27.92,102.27,27.91)

# 获取网格 市场经营主体 行业门类
def getIndustry(start_lon,start_lat,end_lon,end_lat):
    conn = get_db()
    cur = conn.cursor()
    # query = "SELECT hyclass,hycode FROM entity WHERE lon BETWEEN {} AND {} AND lat BETWEEN {} AND {}".format(start_lon,end_lon,end_lat,start_lat)
    query = "SELECT hyclass,hycode FROM entity limit 1000"
    query_result = cur.execute(query)
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
                    "value":category[j]
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
                    "value":count_3_digits[j]
                })
        # 其余门类 
        else:
            category = data['code'].apply(lambda x: x[:2]).value_counts()
            for j in list(category.index):
                industry_result["children"][-1]["children"].append({
                    "name":j,
                    "value":category[j]
                })
    print(industry_result)
    return industry_result


# 获取网格内实体详情
def getIndustryDetail(start_lon,start_lat,end_lon,end_lat):
    conn = get_db()
    cur = conn.cursor()
    # query = "SELECT name,address,businessscope FROM entity WHERE lon BETWEEN {} AND {} AND lat BETWEEN {} AND {}".format(start_lon,end_lon,end_lat,start_lat)
    query = "SELECT name,address,businessscope FROM entity limit 100"
    query_result = cur.execute(query)
    df = pd.DataFrame(query_result.fetchall(),columns=['name','address','businessscope'])
    # print(df)
    entity_result = df.to_dict(orient='records')
    # print(entity_result)
    return entity_result

getIndustryDetail(102.26,27.92,102.27,27.91)