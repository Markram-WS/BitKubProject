from pymongo import MongoClient,results 
import requests 

class database:
   #สร้างตัวแปรที่จำเป็นต้องใช้
    def __init__(self,database,collection,mongodb_srv,line_token):
        self._client=MongoClient(mongodb_srv)
        self._db=self._client.get_database(database)   
        self._collection = collection
        self._line_token = line_token
    
    ####################### ส่วนการเทรด #############################
    
    #โหลดข้อมูลส่วน array ซึ่งจะเก็บสถานะไม้ CS ที่เปิดค้างไว้อยู่
    def load(self):
        if (self._db[self._collection].count_documents({'position':'open'}))==0:
            arr=[]
        else:
            arr=[]
            for data in self._db[self._collection].find({'position':'open'}):
                arr.append(data)
        return arr

    #บันทึกlog ในการยิงคำสั่งแต่ละครัง
    def save(self,arr):
        res = self._db[self._collection].insert_one(arr)
        return res

    def update(self,query,values):
        res = self._db[self._collection].update_one(query, { "$set": values })
        return res


    #----clear worksheet
    def clear(self,target):
        self._db[self._collection].delete_many(target)

        
    def findID(self,ID):
        return print(self._db[self._collection].find_one({"_id": ID}))

    ####################### Msg Line #############################
    def lineMsg(self,msg_line):
        url_line = 'https://notify-api.line.me/api/notify'
        headers_line = {'content-type':'application/x-www-form-urlencoded','Authorization':'Bearer '+self._line_token}
        requests.post(url_line, headers=headers_line , data = {'message':msg_line})