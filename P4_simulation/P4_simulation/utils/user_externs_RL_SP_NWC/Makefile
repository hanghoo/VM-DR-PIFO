CXX=g++
CXXSTD=-std=c++11
CXXFLAGS=$(CXXSTD) -Wall -Wextra -pedantic -g -fPIC
LDFLAGS=-shared

all: RL_SP.so

RL_SP.so:
	$(CXX) $(CXXFLAGS) $(LDFLAGS) RL_SP.cpp -o $@

clean:
	rm -rf RL_SP.so	
	rm -rf RL_SP.o	
	rm -rf RL_SP.lo