/* Android 9 HAL supplement: keep original EDID formats/rates; fix HD channel caps. */
#include <stdint.h>
#include <stddef.h>
#include <sys/ioctl.h>
#include <sound/asound.h>
extern uintptr_t jf_load_bias(void);
extern char *jf_original_cap(const char *,uint32_t);
static int begins(const char *s,const char *prefix){while(*prefix)if(*s++!=*prefix++)return 0;return 1;}
static int channels(const char *text,const char *name){
 int best=0;
 for(const char *p=text;*p;){
  if(begins(p,name)){
   const char *q=p;while(*q && *q!=',')q++;
   if(*q==','){q++;while(*q==' ')q++;int n=0;while(*q>='0' && *q<='9')n=n*10+(*q++-'0');if(n>best)best=n;}
  }
  while(*p && *p!='\n')p++;if(*p)p++;
 }
 return best;
}
static int sink_channels(uint32_t format){
 uintptr_t base=jf_load_bias();
 int (*op)(const char*,int)=(void*)(base+0xd068);
 int (*rd)(int,void*,size_t,size_t)=(void*)(base+0xd074);
 int (*cl)(int)=(void*)(base+0xd080);
 char text[1025];int fd=op("/sys/class/amhdmitx/amhdmitx0/aud_cap",0);
 if(fd<0)return 0;
 int n=rd(fd,text,1024,sizeof(text));cl(fd);
 if(n<1)return 0;
 text[n]=0;
 int count=channels(text,format==0x0e000000?"MAT,":format==0x0c000000?"DTS-HD,":"DTS,");
 if(format==0x0b000000){int hd=channels(text,"DTS-HD,");if(hd>count)count=hd;}
 return count;
}
int jf_hd_supported(uint32_t format){
 return (format==0x0c000000 || format==0x0e000000) && sink_channels(format)>0;
}
char *jf_sink_cap(const char *keys,uint32_t format){
 char *old=jf_original_cap(keys,format);
 if(!old || !begins(old,"sup_channels=") ||
   (format!=0x0b000000 && format!=0x0c000000 && format!=0x0e000000))return old;
 int count=sink_channels(format);
 const char *value=count>=8 ? "sup_channels=AUDIO_CHANNEL_OUT_STEREO|AUDIO_CHANNEL_OUT_5POINT1|AUDIO_CHANNEL_OUT_6POINT1|AUDIO_CHANNEL_OUT_7POINT1" :
  count>=7 ? "sup_channels=AUDIO_CHANNEL_OUT_STEREO|AUDIO_CHANNEL_OUT_5POINT1|AUDIO_CHANNEL_OUT_6POINT1" :
  count>=6 ? "sup_channels=AUDIO_CHANNEL_OUT_STEREO|AUDIO_CHANNEL_OUT_5POINT1" : NULL;
 if(!value)return old;
 uintptr_t base=jf_load_bias();
 char *(*dup)(const char*)=(void*)(base+0xcd8c);
 void (*fr)(void*)=(void*)(base+0xc45c);
 char *result=dup(value);
 if(!result)return old;
 fr(old);return result;
}

/* Old AUGE direct resume always issues PREPARE, discarding partial MAT
 * bursts whenever AudioFlinger briefly runs out of compressed input.
 * Preserve a PREPARED/RUNNING ring; resume PAUSED, recover XRUN explicitly.
 * No sleeps, new buffering thread, or global stream state. */
int jf_truehd_pcm_pause(void *pcm,int pause){
 uintptr_t base=jf_load_bias();
 int (*ctl)(void*,unsigned,...)= (void*)(base+0xcdbc);
 struct snd_pcm_status status;
 for(unsigned i=0;i<sizeof(status);i++)((unsigned char*)&status)[i]=0;
 int rc=ctl(pcm,SNDRV_PCM_IOCTL_STATUS,&status);
 if(rc<0)return ctl(pcm,SNDRV_PCM_IOCTL_PAUSE,pause);
 if(pause){
  if(status.state==SNDRV_PCM_STATE_PREPARED || status.state==SNDRV_PCM_STATE_PAUSED || status.state==SNDRV_PCM_STATE_XRUN)return 0;
  return ctl(pcm,SNDRV_PCM_IOCTL_PAUSE,1);
 }
 if(status.state==SNDRV_PCM_STATE_PAUSED)return ctl(pcm,SNDRV_PCM_IOCTL_PAUSE,0);
 if(status.state==SNDRV_PCM_STATE_PREPARED || status.state==SNDRV_PCM_STATE_RUNNING || status.state==SNDRV_PCM_STATE_DRAINING)return 0;
 return ctl(pcm,SNDRV_PCM_IOCTL_PREPARE);
}

/* Three bytes of verified aml_stream_out padding after bool standby.
 * Streaming BE DTS core boundary detector: never scan core payload for EXSS.
 * state 0..3=sync, 4..7=header, 8=remaining core, 9..12=EXSS.
 * No heap allocation, global stream table, ABI growth, or unbounded buffering.
 */
int jf_dts_boundary(unsigned char *slot,const unsigned char *data,size_t size){
 unsigned st=slot[0],n=(unsigned)slot[1]|((unsigned)slot[2]<<8);
 const unsigned char core[4]={0x7f,0xfe,0x80,0x01};
 const unsigned char exss[4]={0x64,0x58,0x20,0x25};
 if(st>12){st=0;n=0;}
 for(size_t i=0;i<size;i++){
  unsigned b=data[i];
  if(st<4){st=b==core[st]?st+1:(b==core[0]?1:0);}
  else if(st==4){st=5;}
  else if(st==5){n=(b&3)<<12;st=6;}
  else if(st==6){n|=b<<4;st=7;}
  else if(st==7){
   n|=b>>4;n++;
   if(n<96 || n>16384){st=0;n=0;}
   else{n-=8;st=8;}
  }else if(st==8){if(--n==0)st=9;}
  else{
   if(b==exss[st-9]){
    if(++st==13){slot[0]=slot[1]=slot[2]=0;return 1;}
   }else{st=b==core[0]?1:0;n=0;}
  }
 }
 slot[0]=st;slot[1]=n;slot[2]=n>>8;return 0;
}

/* Called only from out_write_direct with both original locks held.
 * Promote actual 48k core+EXSS payloads, not every DTS channel mask.
 * Rebuild with the original lock-free internal standby function; never
 * recursively call out_standby_direct, which would acquire these locks.
 */
void jf_dts_prepare(void *stream,const void *data,size_t size){
 unsigned char *out=stream;
 #define JF_U32(off) (*(uint32_t*)(out+(off)))
 if(JF_U32(0xf4)!=0x0b000000 || JF_U32(0x1ac)!=0x0b000000 ||
    JF_U32(0xf8)!=48000 || (JF_U32(0xfc)&0x440))return;
 if(!jf_dts_boundary(out+0x119,data,size))return;
 if(!jf_hd_supported(0x0c000000))return;
 uintptr_t base=jf_load_bias();
 int (*standby)(void*)=(void*)(base+0x1b8e5);
 if(!out[0x118])standby(stream);
 JF_U32(0x1ac)=0x0c000000;
 JF_U32(0xcc)=192000;
 /* Frame byte counting, delay and original codec selection now all see
  * native DTS_HD; retain the application's public DTS encoding/mask/rate. */
 #undef JF_U32
}
