import csv
import sys
import numpy as np
import matplotlib.pyplot as plt

def getData(filename, mode):
    return data


def getData(filename):
    file = open(filename, 'r')
    reader = csv.reader(file)
    buf_data = []
    out_array = []

    for row in reader:

        buf_data.append(row)
        out_list = []
        for in_data in row:
            if len(in_data) == 0:
                out_data = None
            else:
                out_data = float(in_data)

            out_list.append(out_data)
        out_array.append(out_list)

    file.close()

    return out_array


def makeGraph(list_data, ax, arg_num):

    belt_width = 0.05
    array_data = np.array(list_data)

    intervention_name = ['(proposed) ', '(accel) ', '(brake) ']
    # color_palette = ['royalblue', 'fuchsia', 'slategray']
    color_palette = ['coral', 'olivedrab', 'turquoise', 'royalblue', 'fuchsia', 'gray']

    vel_label = "Velocity "+str(arg_num)
    # if (arg_num == 3):
    #     vel_label = "overconfidence"
    ax.plot(array_data[:, 1], array_data[:, 2], label = vel_label, color=color_palette[arg_num-1])

    for intervention_num in range(4, 7):

        range_flag = 0
        start_itr = 0
        end_itr = 0
        flag = 0

        for itr, data in enumerate(array_data[:, intervention_num]):
            if data != None:
                if range_flag == 0:
                    range_flag = 1
                    start_itr = itr
            else:
                if range_flag == 1:
                    range_flag = 0
                    end_itr = itr
                    x = np.array([array_data[start_itr, 1], array_data[end_itr, 1], array_data[end_itr, 1], array_data[start_itr, 1]])
                    y = np.array([0, 0, 1.0, 1.0])

                    label = "Intervention " + intervention_name[intervention_num-4] + str(arg_num)
                    if flag == 0:
                        ax.fill(x, y, label=label, color=color_palette[arg_num-1], alpha = 0.1)
                        flag = 1
                    else:
                        ax.fill(x, y, color=color_palette[arg_num-1], alpha = 0.1)


    pedestrian_data = array_data[n
    p.argmin(array_data[:, 3])]
    # pedestrian_data = [10.0, 10.0]
    x_pedes = np.array([pedestrian_data[1]-0.1, pedestrian_data[1]+0.1, pedestrian_data[1]+0.1, pedestrian_data[1]-0.1])
    y_pedes = np.array([0, 0, 1.0, 1.0])
    if arg_num == 1:
        ax.fill(x_pedes, y_pedes, color="red", label="pedestrian")
    else:
        ax.fill(x_pedes, y_pedes, color="red")

    print(pedestrian_data)


if __name__ == "__main__":

    args = sys.argv

    fig = plt.figure()
    # fig = plt.figure(figsize=(9, 5))
    # plt.subplots_adjust(left=0.1, right=0.65, top=0.9, bottom=0.15)
    ax = fig.add_subplot(111)

    for arg_num in range(1, len(args)):
        data = getData(args[arg_num])
        makeGraph(data, ax, arg_num)

    # plt.title("Velocity change during intervention with Joystick", fontsize=20, loc='lower center')

    plt.xlabel("Mileage [m]", fontsize=20)
    plt.ylabel("Velocity [m/s]", fontsize=20)
    plt.xlim([0.0, 20.0])
    plt.ylim([0.0, 1.0])
    plt.legend(loc='lower right', fontsize=12)
    # plt.legend(loc='upper left', bbox_to_anchor=(1.05, 1), fontsize=12)
    # plt.show()

    # pngname = args[1] + ".png"
    plt.savefig("fig.png")
