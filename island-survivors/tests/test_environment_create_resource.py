from environment import create_resources

resources = create_resources()

for position, resource in resources.items():
    print(position, resource)