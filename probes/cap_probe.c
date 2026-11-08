#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <dlfcn.h>
int main(int argc,char**argv){
 if(argc!=2)return 2;
 void *h=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
 if(!h){fprintf(stderr,"%s\n",dlerror());return 3;}
 char*(*cap)(const char*,uint32_t)=(void*)dlsym(h,"get_hdmi_sink_cap");
 if(!cap)return 4;
 uint32_t f[]={0x9000000,0xa000000,0xb000000,0xc000000,0xe000000,0xd000000,1};
 for(unsigned i=0;i<sizeof(f)/sizeof(f[0]);i++){
  char *s=cap("sup_channels",f[i]);printf("%08x %s\n",f[i],s?s:"NULL");free(s);
 }
 char *s=cap("sup_formats",0);printf("formats %s\n",s?s:"NULL");free(s);
 dlclose(h);return 0;
}
