sessionid = str(input('sessionid: '))
with open('env.py', 'w') as f1:
    f1.write(f'sessionid = "{sessionid}"')
print('written successfully!')