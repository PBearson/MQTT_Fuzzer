class Parser:

    def insertByte(self, fieldName, payload, index, use_G_field):
        value = self.indexToByte(index + 2, 1, payload)
        if use_G_field:
            self.G_fields[fieldName] = value
        else:
            self.H_fields[fieldName] = value
        return index + 4

    def insertTwoBytes(self, fieldName, payload, index, use_G_field):
        value = self.indexToByte(index + 2, 2, payload)
        if use_G_field:
            self.G_fields[fieldName] = value
        else:
            self.H_fields[fieldName] = value
        return index + 6

    def insertFourBytes(self, fieldName, payload, index, use_G_field):
        value = self.indexToByte(index + 2, 4, payload)
        if use_G_field:
            self.G_fields[fieldName] = value
        else:
            self.H_fields[fieldName] = value
        return index + 10

    def insertString(self, fieldName, payload, index, use_G_field):
        stringLength = int(self.indexToByte(index+2, 2, payload), 16)
        value = self.indexToByte(index + 6, stringLength, payload)
        if use_G_field:
            self.G_fields[fieldName] = value
        else:
            self.H_fields[fieldName] = value
        return index + 6 + (stringLength * 2)

    def insertVariableByteInteger(self, fieldName, payload, index, use_G_field):
        index += 2
        startIndex = index
        multiplier = 1
        while True:
            encodedByte = int(self.indexToByte(index, 1, payload), 16)
            index += 2
            multiplier *= 128
            if encodedByte & 128 == 0:
                break

        value = payload[startIndex:index]
        if use_G_field:
            self.G_fields[fieldName] = value
        else:
            self.H_fields[fieldName] = value
        
        return index

    # This is really just the same as insertString(), but the resulting
    # data is not restricted to ASCII characters. Not relevant for parsing.
    def insertBinaryData(self, fieldName, payload, index, use_G_field):
        return self.insertString(fieldName, payload, index, use_G_field)

    # Called from parseProperties(). This function does the 
    # actual parsing.
    def parsePropertiesHelper(self, properties):
        index = 0
        while index < len(properties):
            if self.indexToByte(index, 1, properties) == '01':
                index = self.insertByte("payload format indicator", properties, index, True)
            
            if self.indexToByte(index, 1, properties) == '02':
                index = self.insertFourBytes("message expiry interval", properties, index, False)

            if self.indexToByte(index, 1, properties) == '03':
                index = self.insertString("content type", properties, index, False)

            if self.indexToByte(index, 1, properties) == '08':
                index = self.insertString("response topic", properties, index, False)

            if self.indexToByte(index, 1, properties) == '09':
                index = self.insertBinaryData("correlation data", properties, index, False)

            if self.indexToByte(index, 1, properties) == '0b':
                index = self.insertVariableByteInteger("subscription identifier", properties, index, False)
            
            if self.indexToByte(index, 1, properties) == '11':
                index = self.insertFourBytes("session expiry interval", properties, index, False)

            if self.indexToByte(index, 1, properties) == '12':
                index = self.insertString("assigned client identifier", properties, index, False)
            
            if self.indexToByte(index, 1, properties) == '13':
                index = self.insertTwoBytes("server keep alive", properties, index, False)
            

            
            break

        

    # Parse the Properties header in the payload.
    # It is assumed that index points to the Property Length field.
    # This function just finds the properties substring within the payload
    # and passes that to parsePropertiesHelper().
    def parseProperties(self):
        multiplier = 1
        propertyLength = 0
        while True:
            encodedByte = int(self.indexToByte(self.index), 16)
            self.index += 2
            propertyLength += (encodedByte & 127) * multiplier
            multiplier *= 128
            if encodedByte & 128 == 0:
                break

        properties = self.indexToByte(self.index, propertyLength)
        self.parsePropertiesHelper(properties)
        self.index += propertyLength
        


    # Given an index in the payload, return the corresponding
    # byte (or several bytes).
    def indexToByte(self, index = None, numBytes = 1, payload = None):
        if index is None:
            index = self.index
        if payload is None:
            payload = self.payload
        return payload[index:index+(numBytes * 2)]

    def __init__(self, payload, protocol_version):
        self.payload = payload
        self.protocol_version = protocol_version
        self.G_fields = {}
        self.H_fields = {}
        self.index = 0

        # Fixed header always goes in G fields
        fixed_header = self.indexToByte()
        self.G_fields["fixed header"] = fixed_header

        # Skip over remaining length field
        self.index = 2
        while int(self.indexToByte(), 16) > 127:
            self.index += 2
        self.index += 2

        