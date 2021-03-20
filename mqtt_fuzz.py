import socket
import random
import time
import sys
import argparse
import math
import select

# Remove bytes in a string
# f : the fuzzable object
# nb : the number of bytes to remove in f
def remove(f, nb):
    for n in range(nb):
        base = random.randint(0, len(f))
        f = f[0:base] + f[base + 1:]

    return f

# Add bytes in a string
# f : the fuzzable object
# nb : the number of bytes to add to f
def add(f, nb):
    for n in range(nb):
        base = random.randint(0, len(f))
        byte = random.getrandbits(8).to_bytes(1, sys.byteorder)
        f = f[0:base] + byte + f[base:]

    return f

# Mutate bytes in a string
# f : the fuzzable object
# nb : the number of bytes to mutate in f
def mutate(f, nb):
    bits = random.sample(range(len(f)), min(nb, len(f)))

    for b in bits:
        byte = random.getrandbits(8).to_bytes(1, sys.byteorder)
        f = f[0:b] + byte + f[b + 1:]

    return f

def get_payload(file):
    f = open(file, "r")
    packets = f.read().splitlines()
    selection = random.choice(packets)
    f.close()
    return bytearray.fromhex(selection)

# Return c / 100 * len(f), where c is a random number between a and b
# a : a number between 0 and 100
# b : a number between a and 100
# f : the fuzzable object 
def select_param_value(f, a, b):
    if a == b:
        c = round(a / 100 * len(f))
    else:
        c = random.choice(range(a, b))
        c = round(c / 100 * len(f))
    return c

def fuzz_target(f, params):
    # Get number of bytes to mutate
    num_mutate_bytes = select_param_value(f, params["min_mutate"], params["max_mutate"])

    # Get number of bytes to add
    if params["super_add_enable"] == 0:
        num_add_bytes = random.randint(params["super_add_min"], params["super_add_max"])
    else:
        num_add_bytes = select_param_value(f, params["min_add"], params["max_add"])

    # Get number of bytes to remove
    num_remove_bytes = select_param_value(f, params["min_remove"], params["max_remove"])

    # Randomize which operations we do
    fuzz_opts = ["mutate", "add", "remove"]

    fuzz_rounds = random.randint(params["min_fuzz_rounds"], params["max_fuzz_rounds"])
    for fr in range(fuzz_rounds):
        fuzz_selection = random.sample(fuzz_opts, random.randint(1, 3))
        for s in fuzz_selection:
            if s == "mutate":
                f = mutate(f, num_mutate_bytes)
            elif s == "add":
                f = add(f, num_add_bytes)
            elif s == "remove":
                f = remove(f, num_remove_bytes)
    return f

# Return a tuple (a, b) where a and b are between abs_min and abs_max and a <= b
def get_min_max(abs_min, abs_max):
    a = random.randint(abs_min, abs_max)
    b = random.randint(abs_min, abs_max)
    if a < b:
        return (a, b)
    return (b, a)

def get_params():
    min_mutate, max_mutate = get_min_max(0, 10 * fuzz_intensity)
    min_add, max_add = get_min_max(0, 10 * fuzz_intensity)
    super_add_min, super_add_max = get_min_max(0, 1000 * fuzz_intensity)
    super_add_enable = random.randint(0, 50)
    min_remove, max_remove = get_min_max(0, 10 * fuzz_intensity)
    min_fuzz_rounds, max_fuzz_rounds = get_min_max(0, fuzz_intensity)

    params = {
        "min_mutate": min_mutate, 
        "max_mutate": max_mutate, 
        "min_add": min_add, 
        "max_add": max_add, 
        "super_add_enable": super_add_enable, 
        "super_add_min": super_add_min,
        "super_add_max": super_add_max,
        "min_remove": min_remove,
        "max_remove": max_remove,
        "min_fuzz_rounds": min_fuzz_rounds,
        "max_fuzz_rounds": max_fuzz_rounds
        }
    return params

def construct_payload(all_payloads):
    # TODO
    payload = all_payloads["connect"] + all_payloads["publish"] + all_payloads["disconnect"]
    return payload
    

# Fuzz MQTT
# params: A dictionary with various parameters
def fuzz(seed):

    random.seed(seed)

    params = get_params()

    all_payloads = {
        "connect": get_payload("mqtt_corpus/CONNECT"),
        "auth": get_payload("mqtt_corpus/AUTH"),
        "publish": get_payload("mqtt_corpus/PUBLISH"),
        "disconnect": get_payload("mqtt_corpus/DISCONNECT")
    }

    unfuzzed_payload = construct_payload(all_payloads)

    all_payloads["connect"] = fuzz_target(all_payloads["connect"], params)
    all_payloads["auth"] = fuzz_target(all_payloads["auth"], params)
    all_payloads["publish"] = fuzz_target(all_payloads["publish"], params)
    all_payloads["disconnect"] = fuzz_target(all_payloads["disconnect"], params)

    payload = construct_payload(all_payloads)
    
    if("payload_only" in globals()):
        print("\nPayload before fuzzing:\n", unfuzzed_payload.hex())
        print("\nPayload after fuzzing:\n", payload.hex())
        exit()

    if(verbosity >= 2):
        print("Unfuzzed payload:\t", unfuzzed_payload.hex())

    if(verbosity >= 1):
        print("Fuzzed payload:\t\t", payload.hex())

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.send(payload)

    ready = select.select([s], [], [], response_delay)

    if ready[0]:
        try:
            response = s.recv(1024)
            if verbosity >= 5:
                print("Broker response:\t", response)
        except ConnectionResetError:
            if verbosity >= 4:
                print("Error:\t\t\t Broker reset connection.")
    else:
        if verbosity >= 4:
            print("Error:\t\t\tBroker was not ready for reading.")
    s.close()

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("-H", "--host", help = "Fuzzing target host. Default is localhost.")
    parser.add_argument("-P", "--port", help = "Fuzzing target port. Default is 1883.")
    parser.add_argument("-s", "--seed", help = "Set the seed. If not set by the user, the system time is used as the seed.")
    parser.add_argument("-fd", "--fuzz_delay", help = "Set the delay between each fuzzing attempt. Default is 0.1 seconds.")
    parser.add_argument("-rd", "--response_delay", help="Set the delay between sending a packet and receiving the response from the broker. Default is 0.1 seconds.")
    parser.add_argument("-m", "--max_runs", help = "Set the number of fuzz attempts made. If not set, the fuzzer will run indefinitely.")
    parser.add_argument("-fi", "--fuzz_intensity", help = "Set the intensity of the fuzzer, from 0 to 10. 0 means packets are not fuzzed at all. Default is 3.")
    parser.add_argument("-ci", "--construct_intensity", help = "Set the intensity of the payload constructer, from 0 to 3. The constructor decides what order to send packets. For example, 0 means all packets begin with CONNECT and end wth DISCONNECT. Default is 0.")
    parser.add_argument("-a", "--autonomous_intensity", help = "If set, the fuzz intensity changes every 1000 runs and the construct intensity changes every 250 runs.", action="store_true")
    parser.add_argument("-v", "--verbosity", help = "Set verbosity, from 0 to 5. 0 means nothing is printed. Default is 1.")
    parser.add_argument("-p1", "--params_only", help = "Do not fuzz. Simply return the parameters based on the seed value.", action = "store_true")
    parser.add_argument("-p2", "--payload_only", help = "Do not fuzz. Simply return the payload before and after it is fuzzed.", action = "store_true")

    args = parser.parse_args()

    global host, port, fuzz_intensity, construct_payload, payload_only, verbosity, response_delay

    if(args.host):
        host = args.host
    else:
        host = "localhost"

    if(args.port):
        port = int(args.port)
    else:
        port = 1883

    if(args.seed):  
        seed = int(args.seed)
    else:
        seed = math.floor(time.time())

    if(args.fuzz_delay):
        fuzz_delay = float(args.fuzz_delay)
    else:
        fuzz_delay = 0.1

    if(args.response_delay):
        response_delay = float(args.response_delay)
    else:
        response_delay = 0.1

    if(args.fuzz_intensity):
        fuzz_intensity = int(args.fuzz_intensity)
        if fuzz_intensity > 10:
            fuzz_intensity = 10
        if fuzz_intensity < 0:
            fuzz_intensity = 0
    else:
        fuzz_intensity = 3

    if(args.construct_intensity):
        construct_intensity = int(args.construct_intensity)
        if construct_intensity > 3:
            construct_intensity = 3
        if construct_intensity < 0:
            construct_intensity = 0
    else:
        construct_intensity = 0

    if(args.max_runs):
        max_runs = int(args.max_runs)

    if(args.autonomous_intensity):
        autonomous_intensity = True
    else:
        autonomous_intensity = False

    if(args.verbosity):
        verbosity = int(args.verbosity)
        if verbosity > 5:
            verbosity = 5
        if verbosity < 0:
            verbosity = 0
    else:
        verbosity = 1


    print("Hello fellow fuzzer :)")
    print("Host: %s, Port: %d" % (host, port))
    print("Base seed: ", seed)
    print("Fuzz Intensity: ", fuzz_intensity)

    if(args.payload_only):
        payload_only = args.payload_only

    if(args.params_only):
        random.seed(seed)
        params = get_params()
        print("\nYour params: ", params)
        if(not args.payload_only):
            exit()

    total_runs = 1
    while True:

        if verbosity >= 1:
            print("\nRun:\t\t\t", total_runs)

        if verbosity >= 3:
            print("Seed:\t\t\t", seed)

        if verbosity >= 4:
            print("Fuzz intensity:\t\t", fuzz_intensity)
            print("Construct intensity:\t", construct_intensity)

        fuzz(seed)
        time.sleep(fuzz_delay)
        total_runs += 1
        seed += 1
        
        if 'max_runs' in locals():
            max_runs -= 1
            if max_runs <= 0:
                break

        if total_runs % 1000 == 0 and autonomous_intensity:
            fuzz_intensity = (fuzz_intensity + 1) % 11

        if total_runs % 250 == 0 and autonomous_intensity:
            construct_intensity = (construct_intensity + 1) % 4

if __name__ == "__main__":
    main(sys.argv[1:])