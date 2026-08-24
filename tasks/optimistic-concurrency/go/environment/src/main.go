package main
import("encoding/json";"net/http";"os";"strconv";"strings";"sync")
type Task struct{ID string `json:"id"`;Title string `json:"title"`;Done bool `json:"done"`}
var mu sync.Mutex; var tasks=map[string]Task{"1":{ID:"1",Title:"calibrate"}}; var next=2
func send(w http.ResponseWriter,status int,v any){w.Header().Set("content-type","application/json");w.WriteHeader(status);if v!=nil{json.NewEncoder(w).Encode(v)}}
func handler(w http.ResponseWriter,r *http.Request){parts:=strings.Split(strings.Trim(r.URL.Path,"/"),"/");if len(parts)<1||parts[0]!="tasks"||len(parts)>2{send(w,404,map[string]string{"error":"not found"});return};id:="";if len(parts)==2{id=parts[1]};mu.Lock();defer mu.Unlock()
 if r.Method=="GET"&&id==""{out:=[]Task{};for _,t:=range tasks{out=append(out,t)};send(w,200,out);return}
 if r.Method=="POST"&&id==""{var in Task;json.NewDecoder(r.Body).Decode(&in);in.ID=strconv.Itoa(next);next++;tasks[in.ID]=in;send(w,201,in);return}
 old,ok:=tasks[id];if !ok{send(w,404,map[string]string{"error":"not found"});return};if r.Method=="GET"{send(w,200,old);return}
 if r.Method=="DELETE"{delete(tasks,id);send(w,204,nil);return};if r.Method=="PUT"||r.Method=="PATCH"{var in Task;json.NewDecoder(r.Body).Decode(&in);if r.Method=="PATCH"{if in.Title==""{in.Title=old.Title};if !in.Done{in.Done=old.Done}};in.ID=id;tasks[id]=in;send(w,200,in);return};send(w,405,nil)}
func main(){http.HandleFunc("/tasks",handler);http.HandleFunc("/tasks/",handler);http.ListenAndServe(":"+env("PORT","8080"),nil)}
func env(k,d string)string{if v:=os.Getenv(k);v!=""{return v};return d}
