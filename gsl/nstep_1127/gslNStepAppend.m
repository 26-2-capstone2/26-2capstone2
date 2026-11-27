function [queue,out]=gslNStepAppend(queue,item,n,gamma)
% Consecutive transitions only. Cut BEFORE any subsequent non-greedy action.
% Off-policy greedy trace cutting; first action may be arbitrary.
queue{end+1}=item;out={};
while numel(queue)>=n || (item.done && ~isempty(queue))
    h=min(n,numel(queue));cut=false;
    for j=2:h
        if ~queue{j}.greedy,h=j-1;cut=true;break;end
    end
    first=queue{1};last=queue{h};reward=0;
    for j=1:h,reward=reward+gamma^(j-1)*queue{j}.reward;end
    if first.index>0
        out{end+1}=struct('S',first.S,'index',first.index,'reward',reward, ...
            'next',last.next,'done',last.done,'discount',gamma^h,'horizon',h,'cut',cut); %#ok<AGROW>
    end
    queue(1)=[];
end
end
