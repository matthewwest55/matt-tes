curl -X POST http://base.themattwest.com/matt-tes/v1/tasks \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Production Custom Image Task",
       "executors": [
         {
           "image": "mwest23/tcga-tes:test",
           "command": ["ls"]
         }
       ]
     }'
