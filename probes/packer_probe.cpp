#include <sys/types.h>
#include <audio_utils/spdif/SPDIFEncoder.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <new>
class Probe final : public android::SPDIFEncoder {
 FILE* file;
public:
 size_t total=0;
 Probe(audio_format_t format,FILE* out):SPDIFEncoder(format),file(out){}
 ssize_t writeOutput(const void* data,size_t size) override {
  size_t result=fwrite(data,1,size,file);total+=result;
  return result==size ? (ssize_t)size : -1;
 }
};
int main(int argc,char** argv){
 if(argc!=5)return 2;
 unsigned format=strtoul(argv[1],nullptr,0),chunk=strtoul(argv[2],nullptr,0);
 FILE *input=fopen(argv[3],"rb"),*output=fopen(argv[4],"wb");
 if(!input||!output||chunk<1||chunk>1048576)return 3;
 static_assert(sizeof(android::SPDIFEncoder)==0x30,"Original ARM32 base ABI changed");
 unsigned char *buf=(unsigned char*)malloc(chunk);
 int result=0;
 {Probe probe((audio_format_t)format,output);size_t n;
  while((n=fread(buf,1,chunk,input))){if(probe.write(buf,n)<0){result=4;break;}}
  printf("base_size=%zu output_bytes=%zu multiplier=%u\n",sizeof(android::SPDIFEncoder),probe.total,probe.getRateMultiplier());
 }
 free(buf);fclose(input);fclose(output);return result;
}
