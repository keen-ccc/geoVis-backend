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
    data = data[(data['X'] >= start_lon) & (data['X'] <= end_lon) & (data['Y'] >= start_lat) & (data['Y'] <= end_lat)]
    population_density = np.mean(data['Z'])
    print(population_density)
    return population_density

def cal_housePrice(start_lon,start_lat,end_lon,end_lat):
    # 非法检测
    # 
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT * FROM houseprice WHERE lon BETWEEN {} AND {} AND lat BETWEEN {} AND {}".format(start_lon,end_lon,start_lat,end_lat)
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
    
    params = (start_lon, end_lon, start_lat, end_lat) * 5
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



cal_populationDensity(103.55,30.55,103.56,30.56)