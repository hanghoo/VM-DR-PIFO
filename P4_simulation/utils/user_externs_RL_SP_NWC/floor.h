#include <bm/bm_sim/logger.h>
#include <bm/bm_sim/extern.h>
#define _STDC_WANT_LIB_EXT1_ 1
#define _CRT_SECURE_NO_WARNINGS
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <vector>
#include <map>
#include <numeric>
#include <chrono>
#include <iostream>


namespace bm {

class floor_extern : public bm::ExternType {
 public:
  BM_EXTERN_ATTRIBUTES {
    BM_EXTERN_ATTRIBUTE_ADD(verbose2);
  }


void init() override {  // Attributes
  static constexpr std::uint32_t QUIET2 = 0u;
  // Init variables
  verbose2_ = verbose2.get<std::uint32_t>() != QUIET2;};


void floor(const Data& nom, const Data& dom, Data& result)
{
	result = Data{int(nom.get<std::uint32_t>() / dom.get<std::uint32_t>())};
} 

 private:
  // Attribute
  Data verbose2{};

  // Data members
  bool verbose2_{false};
};

}  // namespace bm
