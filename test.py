import argparse

#main函数直接接收解析好的参数
def main(name, age):
    print(f"你好 , {name}")
    print(f"今年{age}岁，明年就是{age + 1}岁")
if __name__ == '__main__':
    #1.创建参数解析器
    parser = argparse.ArgumentParser(description='我的练习脚本')

    #2.添加参数
    #位置参数:必填，按顺序传入，不用加前缀
    parser.add_argument('name', type=str, help = '你的名字')


    #可选参数,以 --开头，可传可不传，支持默认值
    parser.add_argument('--age', type=int, default=18, help = '你的年龄')

    #3.解析命令行传入的所有参数
    args = parser.parse_args()

    #4.把参数传给main函数
    main(args.name, args.age)