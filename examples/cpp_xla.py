import sys


def main():
    from parseonly.reader import iter_sources
    from parseonly.cpp import preprocess
    source = sys.argv[1]

    count = 0
    errors = 0
    for fn, source in iter_sources(source, file_exts=['.h']):
        print(f'{fn=} {len(source)=}')
        try:
          source = preprocess(source)
        except Exception as msg:
          print(f'Error: {msg}')
          errors += 1
          continue
        if source is None:
          count += 1
        #print(source)
        print(f'Failure {count=}, Error count={errors}')

if __name__ == "__main__":
    main()
