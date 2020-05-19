numbers = [{'n': 1}, {'n': 2}, {'n': 3}]
letters = ['A', 'B', 'C', 'D']

# data = []
# for n in numbers:
#     for l in letters:
#         n2 = n.copy()
#         n2.update({'l': l})
#         data.append(n2)
data = [{**n, 'l': l} for n in numbers for l in letters]
print(data)
