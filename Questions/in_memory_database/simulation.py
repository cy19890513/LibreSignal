"""
All your implementation code for the bank system simulation goes here.
"""
from dataclasses import field
from sys import prefix

# records {key, fields(dict{})} field (value, deadTime)
class InMemoryDatabase:
    def __init__(self):
        #memoryDatabase (records, fields)
        self.records = {}
        self.backupDict = {} # timestamp: records, remainingLifespan ({})
        #self.fields = {}
    
    # ========== Level 1 Operations ==========
    # `set(key, field, value)` — should insert a field-value pair
    #  to the record associated with key. If the field in the record 
    # already exists, replace the existing value with the specified 
    # value. If the record does not exist, create a new one. This 
    # operation should return an empty string. 
    def set(self,key, field, value):
        if key in self.records:
            self.records[key][field] = value
        else:
            self.records[key] = {field: value}
        return ""
    
    # `get(key, field)` — should return the value contained within field of the record associated with key. If the record or the field doesn't exist, should return an empty string.
    def get(self,key, field):
        if key in self.records and field in self.records[key]:
            #return self.records[key][field]
            #lvl 3
            return self.records[key][field][0]
        else:
            return ""

    # * `delete(key, field)` — should remove the field 
    # from the record associated with key. Returns string
    #  "true" if the field was successfully deleted, and 
    # "false" if the key or the field do not exist in the database.
    def delete(self,key, field):
        if key in self.records and field in self.records[key]:
            del self.records[key][field]
            return "true"
        else:
            return "false"
    
    # ========== Level 2 Operations ==========
    #* `scan(key)` — should return a string representing 
    # the fields of a record associated with key. The returned 
    # string should be in the following format "&lt;field1&gt;(
    # &lt;value1&gt;), &lt;field2&gt;(&lt;value2&gt;), ...", where 
    # fields are sorted lexicographically. If the specified record 
    # does not exist, returns an empty string.
    def scan(self, key):
        fields = self.records.get(key)
        if fields is None:
            return ""
        # fields {field, (value, time)}
        output = ", ".join(f"{f}({v})" for f, (v,t) in sorted(fields.items()))
        return output

    # * `scan_by_prefix(key, prefix)` — should return a string 
    # representing some fields of a record associated with key. 
    # Specifically, only fields that start with prefix should be 
    # included. The returned string should be in the same format 
    # as in the SCAN operation with fields sorted in lexicographical 
    # order.
    def scan_by_prefix(self, key, prefix):
        fields = self.records.get(key)
        #sorted(fields.items())
        if fields is None:
            return ""
        # fields {field, (value, time)}
        #output = ", ".join(f"{x}({y})" for x, y in sorted(fields.items()) if x.startswith(prefix))
        output = ", ".join(f"{f}({v})" for f, (v,t) in sorted(fields.items()) if f.startswith(prefix))
        return output
        

    # ========== Level 3 Operations ==========
    def set_at(self, key, field, value, timestamp):
        expiry = None
        if key in self.records:
            self.records[key][field] = (value,expiry)
        else:
            self.records
            self.records[key] = {field: (value,expiry)}
        return ""

    def set_at_with_ttl(self, key, field, value, timestamp, ttl):
        if key in self.records:
            self.records[key][field] = (value,timestamp+ttl)
        else:
            self.records[key] = {field: (value,timestamp+ttl)}
        return ""

    def delete_at(self, key, field, timestamp):
        
        if key in self.records and field in self.records[key]:
            aliveTime = self.records[key][field][1]
            if timestamp < aliveTime:
                return "false"
            del self.records[key][field]
            return "true"
        else:
            return "false"
    def _is_alive(self, key, field, timestamp):
        if key not in self.records or field not in self.records[key]:
            return False
        value, expiry = self.records[key][field]
        if expiry is None:
            return True
        return timestamp < expiry
    def get_at(self, key, field, timestamp):
        if key in self.records and field in self.records[key]:
            aliveTime = self.records[key][field][1]
            if aliveTime is None or timestamp < aliveTime:
                return self.records[key][field][0]
            else:
                return ""
        else:
            return ""

    def scan_at(self, key, timestamp):
        fields = self.records.get(key)
        if fields is None:
            return ""
        print("YC debug fields:", sorted(fields.items()))
        # ('age', ('30', 106)) 
        items = [(field, v) 
                 for field,(v,deadTime) in sorted(fields.items()) 
                 if deadTime is None or timestamp < deadTime 
        ]
        # field (Value)
        output = ", ".join(f"{x}({y})" for x, y in items)
        return output

    def scan_by_prefix_at(self, key, prefix, timestamp):
        fields = self.records.get(key)
        #sorted(fields.items())
        if fields is None:
            return ""
        items = [(field, v) for field,(v,deadTime) in sorted(fields.items()) if timestamp < deadTime or deadTime is None]

        output = ", ".join(f"{x}({y})" for x, y in items if x.startswith(prefix))
        return output

    # ========== Level 4 Operations ==========
    #     * `backup(timestamp)` — should save the database state at the specified 
    # timestamp, including the remaining lifespan for all records and fields. Remaining 
    # lifespan is the duration between the timestamp of this operation and their expiry 
    # timestamp. Returns a string representing the number of non-empty non-expired 
    # records (the number of keys) in the database.
    # Backup (timestamp, records)
    def backup(self, timestamp):
        self.backupDict[timestamp] = {}
        self.backupDict[timestamp]["records"] = self.records
        self.backupDict[timestamp]["remainingLifespan"] = {}

        for key, fields in self.records.items():
            for field, (value, deadTime) in fields.items():
                if deadTime is None or deadTime > timestamp:
                    remainingLifespan = deadTime - timestamp if deadTime is not None else None
                    if key not in self.backupDict[timestamp]["remainingLifespan"]:
                        self.backupDict[timestamp]["remainingLifespan"][key] = {}
                    
                    self.backupDict[timestamp]["remainingLifespan"][key][field] = remainingLifespan
                
        print("debug YC self.records.items():", self.records.items())
        # (v, deadTime)
        res = 0
        for _, record in self.records.items():
            for fkey, (value, deadTime) in record.items():
                if deadTime is None or deadTime > timestamp:
                    res += 1
        return str(res)
        # return str(len([
        #     fKey
        #     for _, record in self.records.items() 
        #     for fkey, (value, deadTime) in record.items()
        #     if deadTime > timestamp or deadTime is None
        # ]))

    # * `restore(timestamp, timestampToRestore)` — should restore the database 
    # from the latest backup before timestampToRestore. It's guaranteed that a 
    # backup before timestampToRestore will exist. Expiration times for restored
    #  records and fields should be recalculated according to the timestamp of 
    # this operation - since the database timeline always flows forward, restored
    #  records and fields should expire after the timestamp of this operation, 
    # depending on their remaining lifespan in the backup. This operation should 
    # return an empty string.

    def restore(self, timestamp, timestampToRestore):
        #this.backup  timestampToRestore
        # this.records = xxxx
        latest_timestamp = max(
            (timestamp for timestamp in self.backupDict 
            if timestamp <= timestampToRestore),
            default=None
        )

        self.records = self.backupDict[latest_timestamp]["records"]
        for key, fields in self.records.items():
            for field, (value, deadTime) in fields.items():
                remainingLifespan = self.backupDict[latest_timestamp]["remainingLifespan"].get(key, {}).get(field)
                if remainingLifespan is not None:
                    new_deadTime = timestamp + remainingLifespan
                    self.records[key][field] = (value, new_deadTime)
                else:
                    self.records[key][field] = (value, None)



