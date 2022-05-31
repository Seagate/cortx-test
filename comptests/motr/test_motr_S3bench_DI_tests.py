import argparse
import os.path

parser = argparse.ArgumentParser(description='Parse required arguments')
parser.add_argument('--a', help='Access Key')
parser.add_argument('--s', help='Secret Key')
parser.add_argument('--e', help='Endpoint')
args = parser.parse_args()

def s3bench_DI_combinations():
    list_s3bench_DI_comb = [{"TESTCASE_NO" : 1, "noOfClients":10, "noOfSamples":10, "objectSize":"1Mb"}, {"TESTCASE_NO" : 2, "noOfClients":10, "noOfSamples":10, "objectSize":"2Mb"}, {"TESTCASE_NO" : 3, "noOfClients":10, "noOfSamples":10, "objectSize":"3Mb" }, {"TESTCASE_NO" : 4, "noOfClients":10, "noOfSamples":10, "objectSize":"4Mb"}, {"TESTCASE_NO" : 5, "noOfClients":10, "noOfSamples":10, "objectSize":"7Mb"}, {"TESTCASE_NO" : 6, "noOfClients":10, "noOfSamples":10, "objectSize":"8Mb"}, {"TESTCASE_NO" : 7, "noOfClients":10, "noOfSamples":10, "objectSize":"9Mb"}, {"TESTCASE_NO" : 8, "noOfClients":10, "noOfSamples":10, "objectSize":"16Mb"}, {"TESTCASE_NO" : 9, "noOfClients":10, "noOfSamples":10, "objectSize":"32Mb"}, {"TESTCASE_NO" : 10, "noOfClients":10, "noOfSamples":10, "objectSize":"64Mb"}, {"TESTCASE_NO" : 11, "noOfClients":10, "noOfSamples":10, "objectSize":"128Mb"}, {"TESTCASE_NO" : 12, "noOfClients":10, "noOfSamples":10, "objectSize":"85Mb"}, {"TESTCASE_NO" : 13, "noOfClients":10, "noOfSamples":10, "objectSize":"1Kb"}, {"TESTCASE_NO" : 14, "noOfClients":10, "noOfSamples":10, "objectSize":"2Kb"}, {"TESTCASE_NO" : 15, "noOfClients":10, "noOfSamples":10, "objectSize":"3Kb"}, {"TESTCASE_NO" : 16, "noOfClients":10, "noOfSamples":10, "objectSize":"4Kb"}, {"TESTCASE_NO" : 17, "noOfClients":10, "noOfSamples":10, "objectSize":"16Kb"}, {"TESTCASE_NO" : 18, "noOfClients":10, "noOfSamples":10, "objectSize":"32Kb"}, {"TESTCASE_NO" : 19, "noOfClients":10, "noOfSamples":10, "objectSize":"64Kb"}, {"TESTCASE_NO" : 20, "noOfClients":10, "noOfSamples":10, "objectSize":"128Kb"}, {"TESTCASE_NO" : 21, "noOfClients":10, "noOfSamples":10, "objectSize":"1000b"}, {"TESTCASE_NO" : 22, "noOfClients":10, "noOfSamples":10, "objectSize":"2000b"}, {"TESTCASE_NO" : 23, "noOfClients":10, "noOfSamples":10, "objectSize":"3000b"}, {"TESTCASE_NO" : 24, "noOfClients":10, "noOfSamples":10, "objectSize":"5000b"}, {"TESTCASE_NO" : 25, "noOfClients":10, "noOfSamples":10, "objectSize":"7000b"}, {"TESTCASE_NO" : 26, "noOfClients":10, "noOfSamples":10, "objectSize":"7500b"}, {"TESTCASE_NO" : 27, "noOfClients":10, "noOfSamples":10, "objectSize":"9500b"}, {"TESTCASE_NO" : 28, "noOfClients":10, "noOfSamples":10, "objectSize":"17000b"}, {"TESTCASE_NO" : 29, "noOfClients":10, "noOfSamples":10, "objectSize":"19000b"}, {"TESTCASE_NO" : 30, "noOfClients":10, "noOfSamples":10, "objectSize":"19500b"}, {"TESTCASE_NO" : 31, "noOfClients":10, "noOfSamples":10, "objectSize":"50000b"}, {"TESTCASE_NO" : 32, "noOfClients":10, "noOfSamples":10, "objectSize":"70000b"}, {"TESTCASE_NO" : 33, "noOfClients":10, "noOfSamples":10, "objectSize":"75000b"}, {"TESTCASE_NO" : 34, "noOfClients":10, "noOfSamples":10, "objectSize":"90000b"}, {"TESTCASE_NO" : 35, "noOfClients":10, "noOfSamples":10, "objectSize":"95000b"}, {"TESTCASE_NO" : 36, "noOfClients":10, "noOfSamples":10, "objectSize":"123123b"}, {"TESTCASE_NO" : 37, "noOfClients":10, "noOfSamples":10, "objectSize":"123123123b"}, {"TESTCASE_NO" : 38, "noOfClients":10, "noOfSamples":10, "objectSize":"2312b"}, {"TESTCASE_NO" : 39, "noOfClients":10, "noOfSamples":10, "objectSize":"6756b"}, {"TESTCASE_NO" : 40, "noOfClients":10, "noOfSamples":10, "objectSize":"34123b"}, {"TESTCASE_NO" : 41, "noOfClients":10, "noOfSamples":10, "objectSize":"2134123b"}]
     return list_s3bench_DI_comb

def main():
    acsKey    = args.a
    secretKey = args.s
    endPoint  = args.e
    for test in s3bench_DI_combinations():
        command = "s3bench -region us-east-1 -accessKey {} -accessSecret {} -bucket test1 -endpoint {} -numClients {} -numSamples {} -objectSize {}".format(acsKey, secretKey, endPoint, test['noOfClients'], test['noOfSamples'], test['objectSize'])
        os.system(command)

if __name__ == '__main__':
    main()