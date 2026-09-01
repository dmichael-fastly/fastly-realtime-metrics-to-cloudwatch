with open('terraform/variables.tf', 'r') as f:
    lines = f.readlines()

out = []
for line in lines:
    if line.strip() == "}":
        pass
    else:
        out.append(line)

out.append("}\n")

with open('terraform/variables.tf', 'w') as f:
    f.writelines(out)

