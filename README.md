TODO track and log interesting results

TODO add way to restart script if it crashes

TODO need to explain parameters

TODO give option for breaking down the payload packet by packet. It can be an extra option for "payload-only"

TODO construct_intensity option:
    - intensity = 0: start with CONNECT, end with DISCONNECT. No ACKs allowed. No repeat packets.
    - intensity = 1: Packets can be arranged in any order. All packet types allowed. No repeat packets.
    - intensity = 2: Same as above. Packets can be repeated up to 3 times.
    - intensity = 3: Same as above. Packets can be repeated up to 10 times, and payloads themselves can be repeated up to 5 times.