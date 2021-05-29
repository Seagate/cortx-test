import argparse

parser = argparse.ArgumentParser(description='Update the aws credentials file')
parser.add_argument('--access_key',
                    help='aws access key Id')
parser.add_argument('--secret_key',
                    help='aws secret key')
args = parser.parse_args()

ACCESS_KEY=args.access_key
SECRET_KEY=args.secret_key

lines = ['[default]\n','aws_access_key_id = {}\n'.format(ACCESS_KEY),'aws_secret_access_key = {}\n'.format(SECRET_KEY)]

f = open('/root/.aws/credentials','w')
f.writelines(lines)
f.close()

print('Added Credentials')