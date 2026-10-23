"""Execute production condition dispatch and village-state logic against controlled maps."""
from pathlib import Path
import re,sys,subprocess,tempfile
root=Path(sys.argv[1])
def block(text,marker):
 start=text.index(marker);opening=text.index('{',start);depth=0
 for i in range(opening,len(text)):
  depth+=(text[i]=='{')-(text[i]=='}')
  if depth==0:return text[opening:i+1]
 raise AssertionError(marker)
conditions=(root/'src/game/Globals/Conditions.cpp').read_text()
dispatch=block(conditions,'case CONDITION_INSTANCE_SCRIPT:')
source=(root/'src/game/AI/ScriptDevAI/scripts/world/world_map_scripts.cpp').read_text()
body=block(source,'bool ShadeOfTheHorsemanData::IsConditionFulfilled(')
headers=(root/'src/game/Maps/InstanceData.h').read_text()
constants='\n'.join('constexpr uint32 '+name+'='+value+';' for name,value in re.findall(r'(INSTANCE_CONDITION_ID_\w+)\s*=\s*(180\d+)',headers))
areas=sorted(set(re.findall(r'AREAID_\w+',body)))
constants+='\nenum {'+','.join(areas)+'};\n'
constants+='''enum {SHADE_PHASE_ALL_CLEAR,SHADE_PHASE_SPAWNED,SHADE_PHASE_LANDED,SHADE_PHASE_VICTORY};
enum {SHADE_VILLAGE_GOLDSHIRE,SHADE_VILLAGE_KHARANOS,SHADE_VILLAGE_AZURE_WATCH,SHADE_VILLAGE_BRILL,SHADE_VILLAGE_RAZOR_HILL,SHADE_VILLAGE_FALCONWING_SQUARE,MAX_VILLAGES};
'''
code='''#include <cassert>
#include <cstdint>
#include <initializer_list>
using uint32=uint32_t;
'''+constants+'''
struct Map;struct WorldObject {bool isPlayer=false;Map* map=nullptr;bool IsPlayer()const{return isPlayer;}Map* GetMap()const{return map;}};
struct Player:WorldObject {};
struct InstanceData {int calls=0;bool result=false;bool CheckConditionCriteriaMeet(const Player*,uint32,const WorldObject*,int){++calls;return result;}};
struct Map {uint32 id;InstanceData data;uint32 GetId()const{return id;}InstanceData* GetInstanceData()const{return const_cast<InstanceData*>(&data);}};
bool dispatch(const WorldObject* target,const Map* map,const WorldObject* source,uint32 m_value1,int conditionSourceType)
'''+dispatch+'''
struct ShadeOfTheHorsemanData {uint32 m_shadeOfTheHorsemanAttackPhases[MAX_VILLAGES]={};bool IsConditionFulfilled(uint32 conditionId,uint32 areaId)const;};
bool ShadeOfTheHorsemanData::IsConditionFulfilled(uint32 conditionId,uint32 areaId)const
'''+body+'''
int main(){Player player;player.isPlayer=true;
 for(uint32 mapId:{0u,1u,530u,571u,409u,30u}){Map map{mapId};player.map=&map;
  for(uint32 id=18000;id<=18011;++id){map.data.calls=0;map.data.result=true;
   bool allowed=mapId==0||mapId==1||mapId==530;
   assert(dispatch(&player,&map,nullptr,id,12)==allowed);assert(map.data.calls==(allowed?1:0));
   map.data.calls=0;assert(!dispatch(nullptr,&map,&player,id,12));assert(map.data.calls==0);
  }
  map.data.calls=0;map.data.result=false;assert(!dispatch(&player,&map,nullptr,55555,12));assert(map.data.calls==1);
 }
 ShadeOfTheHorsemanData state;
 for(uint32 gold=0;gold<4;++gold)for(uint32 kh=0;kh<4;++kh)for(uint32 az=0;az<4;++az){
  state.m_shadeOfTheHorsemanAttackPhases[SHADE_VILLAGE_GOLDSHIRE]=gold;
  state.m_shadeOfTheHorsemanAttackPhases[SHADE_VILLAGE_KHARANOS]=kh;
  state.m_shadeOfTheHorsemanAttackPhases[SHADE_VILLAGE_AZURE_WATCH]=az;
  assert(state.IsConditionFulfilled(18010,AREAID_GOLDSHIRE)==(gold==0||gold==3));
  assert(state.IsConditionFulfilled(18010,AREAID_KHARANOS)==(kh==0||kh==3));
  assert(state.IsConditionFulfilled(18010,AREAID_AZURE_WATCH)==(az==0||az==3));
  assert(!state.IsConditionFulfilled(18010,999999));
 }
}
'''
with tempfile.TemporaryDirectory(prefix='seasonal-') as folder:
 p=Path(folder);f=p/'test.cpp';f.write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17',str(f),'/Fe:'+str(p/'test.exe'),'/Fo:'+str(p/'test.obj')],check=True)
 subprocess.run([str(p/'test.exe')],check=True)
print('PASS seasonal map dispatch, null player, preserved unknown-condition diagnostics, independent village phases')
