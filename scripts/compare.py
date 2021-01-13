# returns (x,y) index of 'val' in 'my_list'
def index_2d(my_list, val):
    result_x = None
    result_y = None

    for sublist in my_list:
        if val in sublist:
            result_x = my_list.index(sublist)
            result_y = sublist.index(val)
            break

    return result_x, result_y

# returns the number of pairwise comparisons where wotan ordering agrees with vpr ordering. basically match every
# architecture against every other architecture for wotan, and then see if this pairwise odering agrees with VPR. -
# - assumed that architectures are ordered best to worst. first entry is architecture name, second entry is
#   architecture 'score' (min W for VPR)
def compare_wotan_vpr_arch_orderings(wotan_ordering, vpr_ordering, vpr_tolerance=2):
    # Wotan predictions always treated as correct for architectures within specified VPR score tolerance

    # make sure both ordered lists are the same size
    if len(wotan_ordering) != len(vpr_ordering):
        print('expected wotan and vpr ordered list to be the same size')
        sys.exit()

    total_cases = 0
    agree_cases = 0
    agree_within_tolerance = 0

    i = 0
    while i < len(wotan_ordering) - 1:
        j = i + 1
        while j < len(wotan_ordering):
            arch_one = wotan_ordering[i][0]
            arch_two = wotan_ordering[j][0]

            # now get the index of these two arch points in the vpr ordered list. since the lists are sorted from
            # best to worst, a lower index means a better architecture
            vpr_ind_one, dummy = index_2d(vpr_ordering, arch_one)
            vpr_ind_two, dummy = index_2d(vpr_ordering, arch_two)

            vpr_score_one = float(vpr_ordering[vpr_ind_one][1])
            vpr_score_two = float(vpr_ordering[vpr_ind_two][1])

            if vpr_ind_one < vpr_ind_two:
                agree_cases += 1
                agree_within_tolerance += 1
            elif abs(vpr_score_one - vpr_score_two) <= vpr_tolerance:
                agree_within_tolerance += 1
            else:
                print('Disagreed with VPR ordering:\t' + vpr_ordering[vpr_ind_one][0] + ' (' + str(
                    vpr_score_one) + ') VS ' + vpr_ordering[vpr_ind_two][0] + ' (' + str(vpr_score_two) + ')')

            total_cases += 1
            j += 1

        i += 1

    return agree_cases, agree_within_tolerance, total_cases

agree_cases = 0
agree_within_tolerance = 0
total_cases = 0
vpr_tolerance = 2
vpr_arch_ordering = [
    ['0.7_0.7', 123],
    ['0.7_0.3', 139],
    ['0.3_0.3', 155],
    ['0.3_0.6', 160],
    ['0.3_0.7', 172],
    ['0.2_0.4', 184],
    ['0.2_0.2', 192],
    ['0.4_0.2', 226],
]
wotan_arch_ordering = [
    ['0.7_0.7', 17283],
    ['0.7_0.3', 17297],
    ['0.3_0.3', 17363],
    ['0.3_0.6', 17295],
    ['0.3_0.7', 17297],
    ['0.2_0.4', 17407],
    ['0.2_0.2', 18124],
    ['0.4_0.2', 17506],
]

vpr_arch_ordering.sort(key=lambda x: x[1])
wotan_arch_ordering.sort(key=lambda x: x[1])

[agree_cases, agree_within_tolerance, total_cases] = compare_wotan_vpr_arch_orderings(wotan_arch_ordering, vpr_arch_ordering, vpr_tolerance)

print('Wotan and VPR agree in ' + str(agree_cases) + '/' + str(total_cases) + ' pairwise comparisons\n')
print(str(agree_within_tolerance) + '/' + str(total_cases) + ' cases agree within VPR minW tolerance of ' + str(vpr_tolerance))