CXX=g++
CXXSTD=-std=c++11
CXXFLAGS=$(CXXSTD) -Wall -Wextra -pedantic -g -fPIC
LDFLAGS=-shared

all: DRR.so

DRR.so:
	$(CXX) $(CXXFLAGS) $(LDFLAGS) DRR.cpp -o $@

clean:
	rm -rf DRR.so	
	rm -rf DRR.o	
	rm -rf DRR.lo