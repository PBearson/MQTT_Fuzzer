from parser import Parser

class SubscribeParser(Parser):
    def __init__(self, payload, protocol_version):
        super().__init__(payload, protocol_version)

        self.index = self.insertTwoBytesNoIdentifier("packet identifier", payload, self.index, False)

        if protocol_version == 5:
            self.parseProperties()

        topic_num = 0
        while self.index < len(payload):
            self.index = self.insertStringNoIdentifier("topic " + str(topic_num), payload, self.index, False)
            self.index = self.insertByteNoIdentifier("subscription options " + str(topic_num), payload, self.index, True)
            topic_num += 1