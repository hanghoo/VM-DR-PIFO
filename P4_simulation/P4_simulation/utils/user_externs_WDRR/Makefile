CXX=g++
CXXSTD=-std=c++11
CXXFLAGS=$(CXXSTD) -Wall -Wextra -pedantic -g -fPIC
LDFLAGS=-shared

all: WDRR.so

WDRR.so:
	$(CXX) $(CXXFLAGS) $(LDFLAGS) WDRR.cpp -o $@

clean:
	rm -rf WDRR.so	
	rm -rf WDRR.o	
	rm -rf WDRR.lo