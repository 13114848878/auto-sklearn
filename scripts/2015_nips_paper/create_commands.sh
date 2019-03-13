#!/usr/bin/env bash

dir=log_output  # working directory
#task_ids=$(python get_tasks.py)
#task_ids="233 236 242 244 246 248 251 252 253 254 256 258 260 261 262 266 273 275 288 2117 2118 2119 2120 2122 2123 2350 3043 3044 75090 75092 75093 75098 75099 75100 75103 75104 75105 75106 75107 75108 75111 75112 75113 75114 75115 75116 75117 75119 75120 75121 75122 75125 75126 75129 75131 75133 75136 75137 75138 75139 75140 75142 75143 75146 75147 75148 75149 75150 75151 75152 75153 75155 75157 75159 75160 75161 75162 75163 75164 75165 75166 75168 75169 75170 75171 75172 75173 75174 75175 75176 75179 75180 75182 75183 75184 75185 75186 75188 75189 75190 75191 75192 75194 75195 75196 75197 75198 75199 75200 75201 75202 75203 75204 75205 75206 75207 75208 75209 75210 75212 75213 75216 75218 75220 75222 75224 75226 75228 75229 75233 75238 75240 75244 75245 75246 75247 75248 75249 75251 "
#temporarily remove tasks which are not cached
#task_ids="233 236 242 244 246 248 251 252 253 254 258 260 261 262 266 273 275 288 2117 2118 2119 2120 2122 2123 2350 3043 75090 75092 75093 75098 75099 75100 75103 75104 75105 75106 75107 75108 75111 75112 75113 75114 75115 75116 75117 75119 75120 75121 75122 75125 75126 75129 75131 75133 75136 75137 75138 75139 75140 75142 75143 75146 75147 75148 75149 75150 75151 75152 75153 75155 75157 75159 75160 75161 75162 75163 75164 75165 75166 75168 75169 75170 75171 75172 75173 75174 75175 75176 75179 75180 75182 75183 75184 75185 75186 75188 75189 75190 75191 75192 75194 75195 75196 75197 75198 75199 75200 75201 75202 75203 75204 75205 75206 75207 75208 75209 75210 75212 75213 75216 75218 75220 75222 75224 75226 75228 75229 75233 75238 75240 75244 75245 75246 75247 75248 75249 75251 "
task_ids="233 236 242 244 246 248 251 252 253 254 258 260 261 262 266 273 275 288 2117 2118 2119 2120 2122 2123 2350 3043 75090 75092 75093 75098 75099 75100 75103 75104 75105 75106 75107 75108 75111 75112 75113 75114 75115 75116 75117 75119 75120 75121 75122 75125 75126 75129 75131 75133 75136 75137 75138 75139 75140 75142 75143 75146 75147 75148 75149 75150 75151 75152 75153 75155 75157 "
#seeds="1 2 3 4 5 6 7 8 9 10"
seeds="0 1 2 3 4 5"
time_limit=800
per_runtime_limit=80

rm -r commands.txt
#rm -r $dir

# If running on cluster, first copy the cached openml dataset to the home directory.
# This is necessary because there are file handling operations which
# seem to require root permission. Skip this if not running on cluster.
#mkdir -p $dir/cache/org/openml/www/
#cp -R /data/aad/openml/* $dir/cache/org/openml/www

# Create commands
echo "creating commands.txt file..."
for seed in $seeds; do
    for task_id in $task_ids; do
        for model in vanilla metalearning; do
            # put vanilla and ensemble in one folder and meta and meta_ens in another.
            if [ "$model" == "vanilla" ]; then
                cmd="python run_auto_sklearn.py --working-directory $dir/$model --task-id $task_id \
                -s $seed --output-file score_$model.csv --model $model --time-limit $time_limit \
                --per-runtime-limit $per_runtime_limit "
                cmd+="; python run_auto_sklearn.py --working-directory $dir/$model --task-id $task_id \
                -s $seed --output-file score_ensemble.csv --model ensemble --time-limit $time_limit \
                --per-runtime-limit $per_runtime_limit "
            elif [ "$model" == "metalearning" ]; then
                cmd="python run_auto_sklearn.py --working-directory $dir/$model --task-id $task_id \
                -s $seed --output-file score_$model.csv --model $model --time-limit $time_limit \
                --per-runtime-limit $per_runtime_limit "
                cmd+="; python run_auto_sklearn.py --working-directory $dir/$model --task-id $task_id \
                -s $seed --output-file score_meta_ensemble.csv --model meta_ensemble --time-limit $time_limit \
                --per-runtime-limit $per_runtime_limit "
            fi
            echo $cmd >> commands.txt
        done
    done
done
echo "creating commands.txt done"
