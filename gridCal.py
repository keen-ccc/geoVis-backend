import geopandas as gpd

# 读取grids.geojson文件
grids = gpd.read_file('grids.geojson')

# 网格计数（每个网格由四个坐标点构成）
print(grids.head()) #（989000，1）
print(grids.loc[0,'geometry'].centroid.x) 
