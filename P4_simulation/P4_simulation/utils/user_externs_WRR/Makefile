CXX=g++
CXXSTD=-std=c++11
CXXFLAGS=$(CXXSTD) -Wall -Wextra -pedantic -g -fPIC
LDFLAGS=-shared

all: WRR.so

WRR.so:
	$(CXX) $(CXXFLAGS) $(LDFLAGS) WRR.cpp -o $@

clean:
	rm -rf WRR.so	
	rm -rf WRR.o	
	rm -rf WRR.lo