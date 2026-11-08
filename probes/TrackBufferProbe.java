import android.media.AudioTrack;
public class TrackBufferProbe {
 public static void main(String[] args){
  for(int e:new int[]{5,6,7,8,14}){
   int[] masks=e==5||e==6?new int[]{252}:new int[]{252,1276,6396};
   for(int mask:masks){
    AudioTrack t=null;
    try{t=new AudioTrack(3,48000,mask,e,4104,1);
     System.out.println("encoding="+e+" mask="+mask+" state="+t.getState()+" buffer="+t.getBufferSizeInFrames()+" capacity="+t.getBufferCapacityInFrames()+" NO_PLAY_NO_WRITE");
    }catch(Exception ex){System.out.println("encoding="+e+" mask="+mask+" error="+ex);}
    finally{if(t!=null)t.release();}
   }
  }
 }
}
